#!/usr/bin/env python3
"""
Gmail Automation Suite v4.2 - Concurrent Processing Edition

Revolutionary concurrent email processing with dual-thread architecture:
- Producer thread: Continuously searches for unlabeled emails
- Consumer thread: Instantly processes and labels found emails
- Thread-safe queue for seamless email handoff
- Real-time progress tracking across both threads
- Optimized for maximum throughput and efficiency

Author: Gmail Automation Suite
Version: 4.2.0 - Concurrent Edition
"""

import os
import re
import time
import json
import argparse
import warnings
import datetime
import threading
import queue
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import ML categorizer
try:
    from email_ml_categorizer import EmailMLCategorizer, create_synthetic_training_data
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    warnings.warn("ML categorizer not available. Run: pip install -r requirements.txt")

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic',
    'https://www.googleapis.com/auth/gmail.labels'
]

@dataclass
class EmailTask:
    """Represents an email processing task"""
    email_id: str
    email_data: Dict
    metadata: Dict
    priority: int = 0

@dataclass
class ProcessingStats:
    """Thread-safe processing statistics"""
    def __init__(self):
        self.lock = threading.Lock()
        self.emails_found = 0
        self.emails_processed = 0
        self.emails_labeled = 0
        self.emails_skipped = 0
        self.emails_errored = 0
        self.categories = {}
        self.start_time = time.time()
        self.search_complete = False

    def update_found(self, count: int = 1):
        with self.lock:
            self.emails_found += count

    def update_processed(self, count: int = 1):
        with self.lock:
            self.emails_processed += count

    def update_labeled(self, category: str):
        with self.lock:
            self.emails_labeled += 1
            self.categories[category] = self.categories.get(category, 0) + 1

    def update_skipped(self, count: int = 1):
        with self.lock:
            self.emails_skipped += count

    def update_errored(self, count: int = 1):
        with self.lock:
            self.emails_errored += count

    def mark_search_complete(self):
        with self.lock:
            self.search_complete = True

    def get_stats(self) -> Dict:
        with self.lock:
            elapsed = time.time() - self.start_time
            return {
                'emails_found': self.emails_found,
                'emails_processed': self.emails_processed,
                'emails_labeled': self.emails_labeled,
                'emails_skipped': self.emails_skipped,
                'emails_errored': self.emails_errored,
                'categories': self.categories.copy(),
                'elapsed_time': elapsed,
                'search_complete': self.search_complete,
                'processing_rate': self.emails_processed / elapsed if elapsed > 0 else 0
            }

class GmailAutomationConcurrent:
    """Concurrent Gmail automation with producer-consumer architecture"""

    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json',
                 use_ml: bool = True, queue_size: int = 1000):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.labels_cache = {}
        self.categories_config = self.load_categories_config()

        # Thread-safe email queue
        self.email_queue = queue.Queue(maxsize=queue_size)
        self.processing_stats = ProcessingStats()

        # Thread control
        self.stop_event = threading.Event()
        self.search_thread = None
        self.processing_thread = None

        # Initialize ML categorizer
        self.use_ml = use_ml and ML_AVAILABLE
        self.ml_categorizer = None
        if self.use_ml:
            try:
                self.ml_categorizer = EmailMLCategorizer(categories_config=self.categories_config)
                print("🤖 ML categorizer initialized successfully")
            except Exception as e:
                print(f"⚠️ ML categorizer initialization failed: {e}")
                self.use_ml = False

    def load_categories_config(self) -> Dict:
        """Load email categories configuration from JSON file"""
        try:
            with open('email_categories.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ email_categories.json not found. Using default configuration.")
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️ Error reading email_categories.json: {e}")
            return {}

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth 2.0"""
        creds = None

        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"❌ Credentials file not found: {self.credentials_file}")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        return True

    def get_automation_label_ids(self) -> Set[str]:
        """Get set of automation label IDs for filtering"""
        try:
            labels_result = self.service.users().labels().list(userId='me').execute()
            labels = labels_result.get('labels', [])

            automation_labels = set()
            for label in labels:
                label_name = label['name']
                # Check if it's one of our automation labels
                if any(emoji in label_name for emoji in ['🏦', '📈', '🔔', '🛒', '👤', '📰', '🎯', '📦', '🏥', '✈️']):
                    automation_labels.add(label['id'])

            return automation_labels
        except Exception as e:
            print(f"⚠️ Error getting automation labels: {e}")
            return set()

    def get_existing_labels(self) -> Dict[str, str]:
        """Get existing Gmail labels"""
        try:
            result = self.service.users().labels().list(userId='me').execute()
            labels = result.get('labels', [])
            return {label['name']: label['id'] for label in labels}
        except Exception as e:
            print(f"❌ Error getting labels: {e}")
            return {}

    def is_email_unlabeled(self, email_labels: List[str], automation_label_ids: Set[str]) -> bool:
        """Check if an email is unlabeled according to our criteria"""
        # Check if email has any of our automation labels
        has_automation_label = bool(automation_label_ids.intersection(set(email_labels)))
        if has_automation_label:
            return False

        # Check if email has non-system labels (indicating manual organization)
        system_labels = {'INBOX', 'UNREAD', 'IMPORTANT', 'STARRED', 'CATEGORY_PERSONAL',
                        'CATEGORY_SOCIAL', 'CATEGORY_PROMOTIONS', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS',
                        'SENT', 'DRAFT', 'SPAM', 'TRASH', 'CHAT'}

        # Remove system labels from consideration
        non_system_labels = set(email_labels) - system_labels - automation_label_ids

        # If there are non-system, non-automation labels, consider it manually labeled
        if non_system_labels:
            return False

        return True

    def search_unlabeled_emails_producer(self, days_back: int = 0, batch_size: int = 100):
        """
        Producer thread: Continuously searches for unlabeled emails and adds them to queue
        """
        print(f"🔍 Search thread started - scanning for unlabeled emails...")

        # Build Gmail search query
        query_parts = []
        if days_back > 0:
            target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
            date_str = target_date.strftime('%Y/%m/%d')
            query_parts.append(f"after:{date_str}")

        # Exclude categories
        exclude_categories = ['CHAT', 'SENT', 'DRAFT', 'SPAM', 'TRASH']
        for category in exclude_categories:
            query_parts.append(f"-in:{category.lower()}")

        query = ' '.join(query_parts) if query_parts else None

        # Get automation label IDs for filtering
        automation_label_ids = self.get_automation_label_ids()
        print(f"   📋 Found {len(automation_label_ids)} automation labels to check against")

        try:
            next_page_token = None
            total_checked = 0

            while not self.stop_event.is_set():
                # Fetch batch of emails
                request_params = {
                    'userId': 'me',
                    'maxResults': min(batch_size, 500),  # Gmail API limit
                    'q': query
                }

                if next_page_token:
                    request_params['pageToken'] = next_page_token

                try:
                    result = self.service.users().messages().list(**request_params).execute()
                    messages = result.get('messages', [])

                    if not messages:
                        print(f"   📍 Search complete - reached end of inbox ({total_checked} emails checked)")
                        break

                    # Process each email in the batch
                    batch_unlabeled = []
                    for msg in messages:
                        if self.stop_event.is_set():
                            break

                        total_checked += 1

                        # Get email details with labels
                        email = self.service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='metadata',
                            metadataHeaders=['From', 'Subject', 'Date']
                        ).execute()

                        email_labels = email.get('labelIds', [])

                        # Check if this email is unlabeled
                        if self.is_email_unlabeled(email_labels, automation_label_ids):
                            # Extract email data for categorization
                            headers = {h['name'].lower(): h['value'] for h in email.get('payload', {}).get('headers', [])}
                            email_data = {
                                'sender': headers.get('from', ''),
                                'subject': headers.get('subject', ''),
                                'snippet': email.get('snippet', '')
                            }

                            # Create email task
                            task = EmailTask(
                                email_id=msg['id'],
                                email_data=email_data,
                                metadata={'current_labels': email_labels}
                            )

                            # Add to queue (this will block if queue is full)
                            try:
                                self.email_queue.put(task, timeout=5)
                                batch_unlabeled.append(task)
                                self.processing_stats.update_found()
                            except queue.Full:
                                print("   ⚠️ Processing queue full - search thread waiting...")
                                self.email_queue.put(task)  # Block until space available

                    # Progress update
                    if total_checked % 500 == 0:
                        stats = self.processing_stats.get_stats()
                        print(f"   📊 Search progress: {total_checked} checked, {stats['emails_found']} unlabeled found, {stats['emails_processed']} processed")

                    # Get next page token
                    next_page_token = result.get('nextPageToken')
                    if not next_page_token:
                        print(f"   📍 Search complete - reached end of inbox ({total_checked} emails checked)")
                        break

                    # Small delay to respect API limits
                    time.sleep(0.1)

                except HttpError as e:
                    print(f"   ❌ Search error: {e}")
                    time.sleep(2)  # Backoff on error
                    continue

        except Exception as e:
            print(f"❌ Fatal search error: {e}")
        finally:
            # Mark search as complete
            self.processing_stats.mark_search_complete()
            print(f"🏁 Search thread completed - {total_checked} emails checked")

    def process_emails_consumer(self, existing_labels: Dict[str, str], debug: bool = False):
        """
        Consumer thread: Continuously processes emails from queue and applies labels
        """
        print(f"⚡ Processing thread started - waiting for emails to process...")

        processed_count = 0
        while not self.stop_event.is_set():
            try:
                # Get email task from queue (with timeout)
                task = self.email_queue.get(timeout=2)

                if task is None:  # Poison pill to stop processing
                    break

                try:
                    # Categorize email
                    if debug and processed_count < 5:  # Show debug for first few emails
                        debug_info = self.categorize_email_debug(task.email_data)
                        suggested_label = debug_info['final_category']

                        print(f"    🔍 DEBUG: {debug_info['email']['sender'][:30]}")
                        print(f"       Subject: {debug_info['email']['subject']}")
                        if 'ml_prediction' in debug_info:
                            print(f"       ML method: {debug_info.get('method_used', 'unknown')}")
                            print(f"       ML confidence: {debug_info.get('final_confidence', 0):.2f}")
                        print(f"       Final result: {suggested_label}")
                    else:
                        suggested_label = self.categorize_email(task.email_data)

                    self.processing_stats.update_processed()

                    if suggested_label and suggested_label in existing_labels:
                        # Check if email already has this label (shouldn't happen with good filtering)
                        current_labels = task.metadata['current_labels']
                        target_label_id = existing_labels[suggested_label]

                        if target_label_id not in current_labels:
                            # Apply the label
                            self.service.users().messages().modify(
                                userId='me',
                                id=task.email_id,
                                body={'addLabelIds': [target_label_id]}
                            ).execute()

                            self.processing_stats.update_labeled(suggested_label)

                            # Show progress for first few processed
                            if processed_count < 3:
                                sender_short = task.email_data['sender'].split('@')[0] if '@' in task.email_data['sender'] else task.email_data['sender'][:30]
                                subject_short = task.email_data['subject'][:40] + "..." if len(task.email_data['subject']) > 40 else task.email_data['subject']
                                print(f"    ✅ {sender_short[:20]}: {subject_short} → {suggested_label}")
                        else:
                            self.processing_stats.update_skipped()
                    else:
                        self.processing_stats.update_skipped()

                    processed_count += 1

                    # Progress update
                    if processed_count % 50 == 0:
                        stats = self.processing_stats.get_stats()
                        print(f"   ⚡ Processing: {stats['emails_processed']} processed, {stats['emails_labeled']} labeled, rate: {stats['processing_rate']:.1f}/sec")

                    # Rate limiting
                    if processed_count % 10 == 0:
                        time.sleep(0.1)

                except Exception as e:
                    print(f"    ❌ Error processing email {task.email_id}: {e}")
                    self.processing_stats.update_errored()
                finally:
                    self.email_queue.task_done()

            except queue.Empty:
                # Check if search is complete and queue is empty
                stats = self.processing_stats.get_stats()
                if stats['search_complete'] and self.email_queue.empty():
                    print("🏁 Processing thread completed - no more emails to process")
                    break
                continue  # Continue waiting for more emails

        print(f"🏁 Processing thread finished - {processed_count} emails processed")

    def concurrent_scan_and_label(self, days_back: int = 0, debug: bool = False) -> Dict[str, int]:
        """
        Main concurrent processing orchestrator
        """
        print("🚀 Starting concurrent email processing...")
        print(f"📊 Parameters: days_back={days_back}, debug={debug}")
        print("-" * 60)

        # Get existing labels
        existing_labels = self.get_existing_labels()
        if not existing_labels:
            print("❌ No labels found. Please create labels first.")
            return {'error': 'No labels found'}

        print(f"📋 Found {len(existing_labels)} existing labels")

        # Start both threads
        print("🔄 Starting search and processing threads...")

        # Reset stats and stop event
        self.processing_stats = ProcessingStats()
        self.stop_event.clear()

        # Start search thread (producer)
        self.search_thread = threading.Thread(
            target=self.search_unlabeled_emails_producer,
            args=(days_back,),
            name="EmailSearcher"
        )

        # Start processing thread (consumer)
        self.processing_thread = threading.Thread(
            target=self.process_emails_consumer,
            args=(existing_labels, debug),
            name="EmailProcessor"
        )

        # Start threads
        self.search_thread.start()
        self.processing_thread.start()

        try:
            # Monitor progress
            last_stats_time = time.time()
            while self.search_thread.is_alive() or self.processing_thread.is_alive():
                time.sleep(5)  # Update every 5 seconds

                current_time = time.time()
                if current_time - last_stats_time >= 10:  # Detailed stats every 10 seconds
                    stats = self.processing_stats.get_stats()
                    print(f"\n📊 Live Stats (⏱️ {stats['elapsed_time']:.0f}s):")
                    print(f"   🔍 Found: {stats['emails_found']} | ⚡ Processed: {stats['emails_processed']} | ✅ Labeled: {stats['emails_labeled']}")
                    print(f"   📈 Rate: {stats['processing_rate']:.1f} emails/sec | 📦 Queue: {self.email_queue.qsize()}")
                    if stats['categories']:
                        top_categories = sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)[:3]
                        print(f"   🏷️ Top: {', '.join([f'{cat}:{count}' for cat, count in top_categories])}")
                    last_stats_time = current_time

        except KeyboardInterrupt:
            print("\n🛑 Stopping concurrent processing...")
            self.stop_event.set()

        # Wait for threads to complete
        print("⏳ Waiting for threads to complete...")
        self.search_thread.join(timeout=30)
        self.processing_thread.join(timeout=30)

        # Final statistics
        final_stats = self.processing_stats.get_stats()

        print("\n" + "=" * 60)
        print("📊 CONCURRENT EMAIL PROCESSING SUMMARY")
        print("=" * 60)
        print(f"🔍 Total emails found: {final_stats['emails_found']}")
        print(f"⚡ Total processed: {final_stats['emails_processed']}")
        print(f"✅ Successfully labeled: {final_stats['emails_labeled']}")
        print(f"⏭️ Skipped: {final_stats['emails_skipped']}")
        print(f"❌ Errors: {final_stats['emails_errored']}")
        print(f"⏱️ Total time: {final_stats['elapsed_time']:.1f} seconds")
        print(f"📈 Processing rate: {final_stats['processing_rate']:.1f} emails/sec")

        if final_stats['categories']:
            print(f"\n📋 Categories applied:")
            for category, count in sorted(final_stats['categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {category}: {count} emails")

        success_rate = (final_stats['emails_labeled'] / final_stats['emails_processed'] * 100) if final_stats['emails_processed'] > 0 else 0
        print(f"\n📈 Success rate: {success_rate:.1f}%")
        print("🚀 Concurrent processing: Search and labeling ran in parallel")

        print(f"\nConcurrent email processing completed: {final_stats['emails_labeled']} emails labeled")

        return {
            'processed': final_stats['emails_processed'],
            'labeled': final_stats['emails_labeled'],
            'skipped': final_stats['emails_skipped'],
            'errors': final_stats['emails_errored'],
            'categories': final_stats['categories']
        }

    # Import categorization methods from extended version
    def categorize_email(self, email_data: Dict) -> Optional[str]:
        """Advanced email categorization using hybrid ML + rule-based approach."""
        if self.use_ml and self.ml_categorizer:
            rule_based_category = self._categorize_email_rule_based(email_data)
            rule_based_confidence = self._get_rule_based_confidence(email_data, rule_based_category)
            result = self.ml_categorizer.hybrid_categorize(
                email_data,
                rule_based_result=(rule_based_category, rule_based_confidence) if rule_based_category else None
            )
            return result.get('final_category')
        else:
            return self._categorize_email_rule_based(email_data)

    def categorize_email_debug(self, email_data: Dict) -> Dict:
        """Debug version with detailed ML information."""
        categories = self.categories_config.get('categories', {})
        global_settings = self.categories_config.get('global_settings', {})
        confidence_threshold = global_settings.get('confidence_threshold', 0.4)

        category_scores = {}
        for category_name, category_config in categories.items():
            score = self.calculate_category_score(email_data, category_name, category_config)
            category_scores[category_name] = round(score, 3)

        rule_best_category = None
        rule_best_score = 0
        if category_scores:
            rule_best_category = max(category_scores, key=category_scores.get)
            rule_best_score = category_scores[rule_best_category]

        debug_info = {
            'email': {
                'sender': email_data.get('sender', '')[:50],
                'subject': email_data.get('subject', '')[:60],
                'snippet': email_data.get('snippet', '')[:80] + '...'
            },
            'rule_based': {
                'scores': dict(sorted(category_scores.items(), key=lambda x: x[1], reverse=True)),
                'best_category': rule_best_category if rule_best_score >= confidence_threshold else None,
                'confidence': rule_best_score
            }
        }

        if self.use_ml and self.ml_categorizer:
            try:
                rule_based_result = (rule_best_category, rule_best_score) if rule_best_category else None
                ml_result = self.ml_categorizer.hybrid_categorize(email_data, rule_based_result)
                debug_info['ml_prediction'] = ml_result
                debug_info['final_category'] = ml_result.get('final_category')
                debug_info['final_confidence'] = ml_result.get('final_confidence')
                debug_info['method_used'] = ml_result.get('method_used')
            except Exception as e:
                debug_info['ml_error'] = str(e)
        else:
            debug_info['final_category'] = debug_info['rule_based']['best_category']
            debug_info['final_confidence'] = debug_info['rule_based']['confidence']
            debug_info['method_used'] = 'rule_based_only'

        return debug_info

    def calculate_category_score(self, email_data: Dict, category_name: str, category_config: Dict) -> float:
        """Calculate category score (simplified version)"""
        score = 0.0
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()

        # Basic domain matching
        domains = category_config.get('domains', {})
        for domain in domains.get('high_confidence', []):
            if domain in sender:
                score += 1.0

        # Basic keyword matching
        keywords = category_config.get('keywords', {})
        for keyword in keywords.get('subject_high', []):
            if keyword.lower() in subject:
                score += 0.8

        return score

    def _categorize_email_rule_based(self, email_data: Dict) -> Optional[str]:
        """Rule-based categorization"""
        categories = self.categories_config.get('categories', {})
        global_settings = self.categories_config.get('global_settings', {})
        confidence_threshold = global_settings.get('confidence_threshold', 0.4)

        category_scores = {}
        for category_name, category_config in categories.items():
            score = self.calculate_category_score(email_data, category_name, category_config)
            if score > 0:
                category_scores[category_name] = score

        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]
            if best_score >= confidence_threshold:
                return best_category
        return None

    def _get_rule_based_confidence(self, email_data: Dict, category: str) -> float:
        """Get confidence for rule-based categorization"""
        if not category:
            return 0.0
        categories = self.categories_config.get('categories', {})
        if category in categories:
            return self.calculate_category_score(email_data, category, categories[category])
        return 0.0

def main():
    """Concurrent main function"""
    parser = argparse.ArgumentParser(description='Gmail Automation Suite - Concurrent Edition')

    # Basic options
    parser.add_argument('--credentials', default='credentials.json',
                       help='Path to credentials file (default: credentials.json)')
    parser.add_argument('--token', default='token.json',
                       help='Path to token file (default: token.json)')

    # Concurrent processing options
    parser.add_argument('--concurrent-scan', action='store_true',
                       help='Run concurrent scan with parallel search and processing')
    parser.add_argument('--days-back', type=int, default=0,
                       help='Days back to scan (default: 0 = all)')
    parser.add_argument('--queue-size', type=int, default=1000,
                       help='Email queue size for concurrent processing (default: 1000)')
    parser.add_argument('--debug-categorization', action='store_true',
                       help='Show detailed categorization info')

    # ML options
    parser.add_argument('--disable-ml', action='store_true',
                       help='Disable ML categorization')
    parser.add_argument('--ml-info', action='store_true',
                       help='Show ML model information')
    parser.add_argument('--bootstrap-training', action='store_true',
                       help='Bootstrap ML model training')

    args = parser.parse_args()

    # Initialize automation
    automation = GmailAutomationConcurrent(
        args.credentials,
        args.token,
        use_ml=not args.disable_ml,
        queue_size=args.queue_size
    )

    print("🔍 Validating environment...")
    if not automation.authenticate():
        print("❌ Authentication failed")
        return 1
    print("✅ Authentication successful!")

    # Handle ML operations
    if args.ml_info:
        if automation.use_ml and automation.ml_categorizer:
            info = automation.ml_categorizer.get_model_info()
            print("\n🤖 ML Model Information:")
            print("=" * 50)
            for key, value in info.items():
                if key == 'categories':
                    print(f"   {key}: {len(value)} categories")
                    for cat in value:
                        print(f"      • {cat}")
                else:
                    print(f"   {key}: {value}")
        else:
            print("⚠️ ML categorization is not enabled")
        return 0

    if args.bootstrap_training:
        if automation.use_ml and automation.ml_categorizer:
            print("🔄 Creating synthetic training data...")
            synthetic_data = create_synthetic_training_data(automation.categories_config)
            print(f"✅ Generated {len(synthetic_data)} synthetic examples")
            if len(synthetic_data) > 0:
                print("🔄 Training initial ML model...")
                report = automation.ml_categorizer.train_classifier(synthetic_data)
                print(f"✅ Training completed with accuracy: {report['accuracy']:.3f}")
        else:
            print("⚠️ ML categorization is not enabled")
        return 0

    # Handle concurrent processing
    if args.concurrent_scan:
        stats = automation.concurrent_scan_and_label(
            days_back=args.days_back,
            debug=args.debug_categorization
        )
        return 0 if stats.get('errors', 0) == 0 else 1

    # Default behavior
    print("🎯 Concurrent Gmail Automation Suite v4.2")
    print("💡 Use --concurrent-scan for parallel search and processing")
    print("💡 Use --days-back N to limit scan timeframe")
    print("💡 Use --queue-size N to adjust concurrent processing buffer")
    print("💡 Use --help for all available options")

    return 0

if __name__ == "__main__":
    exit(main())