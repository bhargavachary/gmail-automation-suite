"""
Email Classification Cache System

Provides persistent storage for email classifications with indexing,
resume functionality, and efficient lookup operations.
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timezone
from dataclasses import asdict
import uuid

from ..models.email import Email
from ..utils.logger import get_logger

logger = get_logger(__name__)


def serialize_email_data(email: Email) -> str:
    """Serialize email data to JSON string with datetime handling."""
    def datetime_handler(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(asdict(email), default=datetime_handler)


class EmailCacheError(Exception):
    """Email cache related errors."""
    pass


class EmailCache:
    """
    Persistent email classification cache with SQLite backend.

    Features:
    - Email deduplication by message ID
    - Classification result storage
    - Label application tracking
    - Resume functionality
    - Efficient batch operations
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize email cache.

        Args:
            cache_dir: Directory for cache storage
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "email_cache.db"
        self.index_file = self.cache_dir / "email_index.json"

        # Initialize database
        self._init_database()

        # Load in-memory index for fast lookups
        self._load_index()

        logger.info(f"Email cache initialized at {self.cache_dir}")

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    subject TEXT,
                    sender TEXT,
                    receiver TEXT,
                    date_received TEXT,
                    snippet TEXT,
                    content_hash TEXT,
                    processed_at TEXT,
                    classification_method TEXT,
                    classified_category TEXT,
                    classification_confidence REAL,
                    label_applied BOOLEAN DEFAULT FALSE,
                    label_applied_at TEXT,
                    raw_data TEXT
                )
            """)

            # Create indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_message_id ON emails(message_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_classification ON emails(classified_category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_label_applied ON emails(label_applied)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_processed_at ON emails(processed_at)")

            conn.commit()

    def _load_index(self) -> None:
        """Load in-memory index for fast lookups."""
        self._processed_messages: Set[str] = set()
        self._labeled_messages: Set[str] = set()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load processed message IDs
                cursor = conn.execute("SELECT message_id FROM emails")
                self._processed_messages = {row[0] for row in cursor.fetchall()}

                # Load labeled message IDs
                cursor = conn.execute("SELECT message_id FROM emails WHERE label_applied = TRUE")
                self._labeled_messages = {row[0] for row in cursor.fetchall()}

            logger.info(f"Loaded {len(self._processed_messages)} processed emails, "
                       f"{len(self._labeled_messages)} labeled emails from cache")

        except sqlite3.Error as e:
            logger.warning(f"Failed to load index: {e}")
            self._processed_messages = set()
            self._labeled_messages = set()

    def _compute_content_hash(self, email: Email) -> str:
        """Compute hash of email content for deduplication."""
        content = f"{email.headers.subject}|{email.content.combined_text}|{email.headers.from_address}"
        return hashlib.md5(content.encode()).hexdigest()

    def is_processed(self, message_id: str) -> bool:
        """Check if email has been processed."""
        return message_id in self._processed_messages

    def is_labeled(self, message_id: str) -> bool:
        """Check if email has been labeled."""
        return message_id in self._labeled_messages

    def get_unlabeled_classified_emails(self) -> List[Tuple[str, str, float]]:
        """
        Get emails that are classified but not labeled.

        Returns:
            List of (message_id, category, confidence) tuples
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT message_id, classified_category, classification_confidence
                    FROM emails
                    WHERE classified_category IS NOT NULL
                    AND label_applied = FALSE
                """)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Failed to get unlabeled emails: {e}")
            return []

    def store_email(self, email: Email, classification_result=None, method: str = "unknown") -> None:
        """
        Store email and its classification result.

        Args:
            email: Email object
            classification_result: Classification result object
            method: Classification method used
        """
        try:
            content_hash = self._compute_content_hash(email)
            now = datetime.now(timezone.utc).isoformat()

            # Prepare data
            data = {
                'message_id': email.metadata.message_id,
                'thread_id': email.metadata.thread_id,
                'subject': email.headers.subject,
                'sender': email.headers.from_address,
                'receiver': ', '.join(email.headers.to_addresses),
                'date_received': email.headers.date.isoformat() if email.headers.date else None,
                'snippet': email.metadata.snippet,
                'content_hash': content_hash,
                'processed_at': now,
                'classification_method': method,
                'classified_category': classification_result.category if classification_result else None,
                'classification_confidence': classification_result.confidence if classification_result else None,
                'label_applied': False,
                'label_applied_at': None,
                'raw_data': serialize_email_data(email)
            }

            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO emails (
                        message_id, thread_id, subject, sender, receiver,
                        date_received, snippet, content_hash, processed_at,
                        classification_method, classified_category,
                        classification_confidence, label_applied, label_applied_at, raw_data
                    ) VALUES (
                        :message_id, :thread_id, :subject, :sender, :receiver,
                        :date_received, :snippet, :content_hash, :processed_at,
                        :classification_method, :classified_category,
                        :classification_confidence, :label_applied, :label_applied_at, :raw_data
                    )
                """, data)
                conn.commit()

            # Update in-memory index
            self._processed_messages.add(email.metadata.message_id)

            logger.debug(f"Stored email {email.metadata.message_id} with classification: "
                        f"{classification_result.category if classification_result else 'None'}")

        except sqlite3.Error as e:
            logger.error(f"Failed to store email {email.metadata.message_id}: {e}")
            raise EmailCacheError(f"Database error: {e}")

    def mark_labeled(self, message_id: str) -> None:
        """Mark email as labeled in Gmail."""
        try:
            now = datetime.now(timezone.utc).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE emails
                    SET label_applied = TRUE, label_applied_at = ?
                    WHERE message_id = ?
                """, (now, message_id))
                conn.commit()

            # Update in-memory index
            self._labeled_messages.add(message_id)

            logger.debug(f"Marked email {message_id} as labeled")

        except sqlite3.Error as e:
            logger.error(f"Failed to mark email {message_id} as labeled: {e}")
            raise EmailCacheError(f"Database error: {e}")

    def batch_mark_labeled(self, message_ids: List[str]) -> None:
        """Mark multiple emails as labeled."""
        try:
            now = datetime.now(timezone.utc).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.executemany("""
                    UPDATE emails
                    SET label_applied = TRUE, label_applied_at = ?
                    WHERE message_id = ?
                """, [(now, mid) for mid in message_ids])
                conn.commit()

            # Update in-memory index
            self._labeled_messages.update(message_ids)

            logger.info(f"Marked {len(message_ids)} emails as labeled")

        except sqlite3.Error as e:
            logger.error(f"Failed to batch mark emails as labeled: {e}")
            raise EmailCacheError(f"Database error: {e}")

    def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics from cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total counts
                total_processed = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
                total_classified = conn.execute(
                    "SELECT COUNT(*) FROM emails WHERE classified_category IS NOT NULL"
                ).fetchone()[0]
                total_labeled = conn.execute(
                    "SELECT COUNT(*) FROM emails WHERE label_applied = TRUE"
                ).fetchone()[0]

                # Category distribution
                cursor = conn.execute("""
                    SELECT classified_category, COUNT(*)
                    FROM emails
                    WHERE classified_category IS NOT NULL
                    GROUP BY classified_category
                """)
                category_dist = dict(cursor.fetchall())

                # Method distribution
                cursor = conn.execute("""
                    SELECT classification_method, COUNT(*)
                    FROM emails
                    WHERE classification_method IS NOT NULL
                    GROUP BY classification_method
                """)
                method_dist = dict(cursor.fetchall())

                return {
                    'total_processed': total_processed,
                    'total_classified': total_classified,
                    'total_labeled': total_labeled,
                    'classification_rate': total_classified / total_processed if total_processed > 0 else 0,
                    'labeling_rate': total_labeled / total_classified if total_classified > 0 else 0,
                    'category_distribution': category_dist,
                    'method_distribution': method_dist,
                    'pending_labels': total_classified - total_labeled
                }

        except sqlite3.Error as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def filter_unprocessed_messages(self, message_ids: List[str]) -> List[str]:
        """Filter out already processed messages."""
        return [mid for mid in message_ids if not self.is_processed(mid)]

    def get_cached_classification(self, message_id: str) -> Optional[Tuple[str, float]]:
        """Get cached classification result."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT classified_category, classification_confidence
                    FROM emails
                    WHERE message_id = ? AND classified_category IS NOT NULL
                """, (message_id,))
                result = cursor.fetchone()
                return result if result else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get cached classification: {e}")
            return None

    def export_classifications(self, output_file: Path) -> None:
        """Export all classifications to JSON."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT message_id, subject, sender, classified_category,
                           classification_confidence, label_applied, processed_at
                    FROM emails
                    WHERE classified_category IS NOT NULL
                    ORDER BY processed_at DESC
                """)

                results = []
                for row in cursor.fetchall():
                    results.append({
                        'message_id': row[0],
                        'subject': row[1],
                        'sender': row[2],
                        'category': row[3],
                        'confidence': row[4],
                        'labeled': bool(row[5]),
                        'processed_at': row[6]
                    })

                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)

                logger.info(f"Exported {len(results)} classifications to {output_file}")

        except (sqlite3.Error, IOError) as e:
            logger.error(f"Failed to export classifications: {e}")
            raise EmailCacheError(f"Export error: {e}")

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days."""
        try:
            cutoff = datetime.now(timezone.utc).replace(
                day=datetime.now().day - days
            ).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM emails
                    WHERE processed_at < ? AND label_applied = TRUE
                """, (cutoff,))
                deleted_count = cursor.rowcount
                conn.commit()

            # Refresh index
            self._load_index()

            logger.info(f"Cleaned up {deleted_count} old cache entries")
            return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return 0