"""
Gmail API client for Gmail Automation Suite.

Provides high-level interface for Gmail operations including
authentication, email retrieval, labeling, and batch operations.
"""

import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models.email import Email
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GmailClientError(Exception):
    """Gmail client related errors."""
    pass


class GmailClient:
    """
    High-level Gmail API client.

    Handles authentication, email operations, and label management
    with proper error handling and rate limiting.
    """

    # Required Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.settings.basic',
        'https://www.googleapis.com/auth/gmail.labels'
    ]

    def __init__(self,
                 credentials_file: str = "credentials.json",
                 token_file: str = "token.json",
                 config_dir: Optional[Path] = None):
        """
        Initialize Gmail client.

        Args:
            credentials_file: OAuth2 credentials file from Google Cloud Console
            token_file: Token storage file (auto-generated)
            config_dir: Configuration directory (default: current directory)
        """
        self.config_dir = config_dir or Path(".")

        # Handle absolute vs relative paths
        if Path(credentials_file).is_absolute():
            self.credentials_file = Path(credentials_file)
        else:
            self.credentials_file = self.config_dir / credentials_file

        if Path(token_file).is_absolute():
            self.token_file = Path(token_file)
        else:
            self.token_file = self.config_dir / token_file
        self.service = None
        self.user_id = "me"

        # Initialize Gmail service
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2."""
        creds = None

        # Load existing token
        if self.token_file.exists():
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing authentication token")
            except Exception as e:
                logger.warning(f"Failed to load token file: {e}")

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed authentication token")
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None

            if not creds:
                if not self.credentials_file.exists():
                    raise GmailClientError(
                        f"Credentials file not found: {self.credentials_file}. "
                        "Please download it from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Obtained new authentication token")

            # Save credentials
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Saved authentication token to {self.token_file}")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")

        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized successfully")
        except Exception as e:
            raise GmailClientError(f"Failed to build Gmail service: {e}")

    def get_labels(self) -> Dict[str, str]:
        """
        Get all Gmail labels.

        Returns:
            Dictionary mapping label names to label IDs
        """
        try:
            results = self.service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])

            return {label['name']: label['id'] for label in labels}

        except HttpError as e:
            logger.error(f"Failed to get labels: {e}")
            raise GmailClientError(f"Failed to retrieve labels: {e}")

    def create_label(self, name: str, color: Optional[Dict[str, str]] = None) -> str:
        """
        Create a new Gmail label.

        Args:
            name: Label name
            color: Optional color configuration

        Returns:
            Created label ID
        """
        try:
            label_object = {
                'name': name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }

            if color:
                label_object['color'] = color

            result = self.service.users().labels().create(
                userId=self.user_id,
                body=label_object
            ).execute()

            label_id = result['id']
            logger.info(f"Created label '{name}' with ID: {label_id}")
            return label_id

        except HttpError as e:
            if 'already exists' in str(e).lower():
                logger.warning(f"Label '{name}' already exists")
                # Get existing label ID
                labels = self.get_labels()
                return labels.get(name, '')
            else:
                logger.error(f"Failed to create label '{name}': {e}")
                raise GmailClientError(f"Failed to create label: {e}")

    def delete_label(self, label_id: str) -> None:
        """
        Delete a Gmail label by ID.

        Args:
            label_id: Gmail label ID to delete

        Note:
            This permanently deletes the label and removes it from all messages.
            System labels cannot be deleted.
        """
        try:
            self.service.users().labels().delete(
                userId=self.user_id,
                id=label_id
            ).execute()

            logger.info(f"Deleted label with ID: {label_id}")

        except HttpError as e:
            if 'not found' in str(e).lower():
                logger.warning(f"Label {label_id} not found (may already be deleted)")
            elif 'system label' in str(e).lower() or 'cannot delete' in str(e).lower():
                logger.warning(f"Cannot delete system label: {label_id}")
                raise GmailClientError(f"Cannot delete system label: {label_id}")
            else:
                logger.error(f"Failed to delete label {label_id}: {e}")
                raise GmailClientError(f"Failed to delete label: {e}")

    def search_messages(self,
                       query: str = "",
                       max_results: Optional[int] = 100) -> List[str]:
        """
        Search for messages using Gmail search syntax.

        Args:
            query: Gmail search query (e.g., "is:unread", "from:example.com")
            max_results: Maximum number of messages to return (None for exhaustive search)

        Returns:
            List of message IDs
        """
        try:
            message_ids = []
            page_token = None

            while True:
                # Calculate page size
                if max_results is None:
                    # Exhaustive search - use max page size
                    page_size = 500
                else:
                    # Limited search - calculate remaining
                    remaining = max_results - len(message_ids)
                    if remaining <= 0:
                        break
                    page_size = min(remaining, 500)  # Gmail API max per page

                result = self.service.users().messages().list(
                    userId=self.user_id,
                    q=query,
                    maxResults=page_size,
                    pageToken=page_token
                ).execute()

                messages = result.get('messages', [])
                message_ids.extend([msg['id'] for msg in messages])

                page_token = result.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"Found {len(message_ids)} messages for query: '{query}'")
            return message_ids if max_results is None else message_ids[:max_results]

        except HttpError as e:
            logger.error(f"Failed to search messages: {e}")
            raise GmailClientError(f"Failed to search messages: {e}")

    def get_message(self, message_id: str, format: str = "full") -> Email:
        """
        Get a specific message by ID.

        Args:
            message_id: Gmail message ID
            format: Message format ("full", "minimal", "raw", "metadata")

        Returns:
            Email object
        """
        try:
            message = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id,
                format=format
            ).execute()

            return Email.from_gmail_message(message)

        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise GmailClientError(f"Failed to retrieve message: {e}")

    def get_messages_batch(self,
                          message_ids: List[str],
                          format: str = "full",
                          max_workers: int = 1) -> Iterator[Email]:
        """
        Get multiple messages efficiently with progress reporting.

        Args:
            message_ids: List of Gmail message IDs
            format: Message format for all messages
            max_workers: Ignored - kept for API compatibility

        Yields:
            Email objects
        """
        total = len(message_ids)
        logger.info(f"Fetching {total} messages sequentially...")

        for idx, message_id in enumerate(message_ids, 1):
            try:
                email = self._get_message_with_retry(message_id, format)
                if email:
                    yield email

                # Progress every 50 messages or at milestones
                if idx % 50 == 0 or idx in [10, 25, 100, 250, 500, 1000]:
                    progress_pct = (idx / total) * 100
                    rate = idx / ((idx * 0.35))  # ~0.35s per message estimate
                    remaining = (total - idx) * 0.35 / 60  # minutes
                    logger.info(f"Progress: {idx}/{total} ({progress_pct:.1f}%) - ~{remaining:.1f} min remaining")

            except Exception as e:
                logger.warning(f"Failed to get message {message_id}: {e}")
                continue

    def _get_message_with_retry(self, message_id: str, format: str = "full") -> Optional[Email]:
        """
        Get message with retry logic for handling connection issues.

        Args:
            message_id: Gmail message ID
            format: Message format

        Returns:
            Email object or None if failed
        """
        import time
        import random
        from googleapiclient.errors import HttpError

        max_retries = 3
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                return self.get_message(message_id, format)
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"Rate limit hit for {message_id}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                    time.sleep(delay)
                    continue
                elif e.resp.status >= 500:  # Server errors
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.debug(f"Server error for {message_id}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                    time.sleep(delay)
                    continue
                else:
                    logger.warning(f"HTTP error {e.resp.status} for {message_id}: {e}")
                    return None
            except Exception as e:
                error_str = str(e).lower()
                if any(term in error_str for term in ["ssl", "connection", "incompleteread", "nonetype", "timeout", "reset", "broken pipe"]):
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"Connection error for {message_id}, retrying in {delay:.2f}s (attempt {attempt + 1}): {e}")
                    time.sleep(delay)
                    continue
                else:
                    logger.warning(f"Get message failed for {message_id}: {e}")
                    return None

        logger.warning(f"Failed to get message {message_id} after {max_retries} attempts")
        return None

    def add_label(self, message_id: str, label_id: str) -> None:
        """
        Add a label to a message with robust error handling and retry logic.

        Args:
            message_id: Gmail message ID
            label_id: Gmail label ID
        """
        import time
        import random

        max_retries = 3
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                # First verify the message still exists
                try:
                    self.service.users().messages().get(
                        userId=self.user_id,
                        id=message_id,
                        format='minimal'
                    ).execute()
                except HttpError as e:
                    if e.resp.status == 404:
                        logger.warning(f"Message {message_id} no longer exists, skipping label application")
                        return
                    raise e

                # Apply the label
                self.service.users().messages().modify(
                    userId=self.user_id,
                    id=message_id,
                    body={'addLabelIds': [label_id]}
                ).execute()

                logger.debug(f"Added label {label_id} to message {message_id}")
                return

            except HttpError as e:
                if e.resp.status == 400 and "Precondition check failed" in str(e):
                    # Message state has changed, wait and retry
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                        logger.debug(f"Precondition failed for {message_id}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.warning(f"Precondition check failed for message {message_id} after {max_retries} attempts - skipping")
                        return
                elif e.resp.status == 404:
                    logger.warning(f"Message {message_id} not found - may have been deleted")
                    return
                elif e.resp.status == 429:
                    # Rate limit - exponential backoff
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"Rate limit hit for {message_id}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Failed to add label to message {message_id}: {e}")
                    raise GmailClientError(f"Failed to add label: {e}")
            except Exception as e:
                logger.error(f"Unexpected error adding label to message {message_id}: {e}")
                raise GmailClientError(f"Failed to add label: {e}")

        logger.warning(f"Failed to add label to message {message_id} after {max_retries} attempts")

    def add_labels_batch(self, message_ids: List[str], label_id: str) -> Dict[str, int]:
        """
        Add a single label to multiple messages efficiently.

        Args:
            message_ids: List of Gmail message IDs
            label_id: Gmail label ID to add

        Returns:
            Dictionary with success/failure counts
        """
        return self.batch_modify_labels(
            message_ids=message_ids,
            add_label_ids=[label_id]
        )

    def remove_label(self, message_id: str, label_id: str) -> None:
        """
        Remove a label from a message.

        Args:
            message_id: Gmail message ID
            label_id: Gmail label ID
        """
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={'removeLabelIds': [label_id]}
            ).execute()

            logger.debug(f"Removed label {label_id} from message {message_id}")

        except HttpError as e:
            logger.error(f"Failed to remove label from message {message_id}: {e}")
            raise GmailClientError(f"Failed to remove label: {e}")

    def batch_modify_labels(self,
                           message_ids: List[str],
                           add_label_ids: Optional[List[str]] = None,
                           remove_label_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Modify labels for multiple messages in batches with robust error handling.

        Args:
            message_ids: List of Gmail message IDs
            add_label_ids: Label IDs to add
            remove_label_ids: Label IDs to remove

        Returns:
            Dictionary with success/failure counts
        """
        if not add_label_ids and not remove_label_ids:
            return {'success': 0, 'failed': 0, 'skipped': 0}

        import time
        import random

        # Process in smaller batches to avoid API limits and reduce failure impact
        batch_size = 100
        total_success = 0
        total_failed = 0
        total_skipped = 0

        total_batches = (len(message_ids) + batch_size - 1) // batch_size

        for i in range(0, len(message_ids), batch_size):
            batch_ids = message_ids[i:i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(f"Processing label batch {batch_num}/{total_batches} ({len(batch_ids)} messages)")

            # Try batch modification first
            success = False
            for attempt in range(3):
                try:
                    body = {'ids': batch_ids}

                    if add_label_ids:
                        body['addLabelIds'] = add_label_ids

                    if remove_label_ids:
                        body['removeLabelIds'] = remove_label_ids

                    self.service.users().messages().batchModify(
                        userId=self.user_id,
                        body=body
                    ).execute()

                    total_success += len(batch_ids)
                    logger.debug(f"Batch modified labels for {len(batch_ids)} messages")
                    success = True
                    break

                except HttpError as e:
                    if e.resp.status == 429:  # Rate limit
                        delay = 0.5 * (2 ** attempt) + random.uniform(0, 1)
                        logger.debug(f"Rate limit hit for batch {batch_num}, retrying in {delay:.2f}s")
                        time.sleep(delay)
                        continue
                    elif e.resp.status == 400 and "Precondition check failed" in str(e):
                        # Some messages in batch have changed state, fall back to individual processing
                        logger.info(f"Precondition failed for batch {batch_num}, processing individually")
                        break
                    else:
                        logger.warning(f"Batch modify failed for batch {batch_num}: {e}")
                        break
                except Exception as e:
                    logger.warning(f"Unexpected error in batch {batch_num}: {e}")
                    break

            # Fall back to individual processing if batch failed
            if not success:
                logger.debug(f"Falling back to individual processing for batch {batch_num}")
                for message_id in batch_ids:
                    try:
                        if add_label_ids:
                            for label_id in add_label_ids:
                                self.add_label(message_id, label_id)
                        if remove_label_ids:
                            for label_id in remove_label_ids:
                                self.remove_label(message_id, label_id)
                        total_success += 1
                    except Exception as e:
                        if "no longer exists" in str(e) or "not found" in str(e):
                            total_skipped += 1
                        else:
                            total_failed += 1
                            logger.warning(f"Failed to modify labels for {message_id}: {e}")

            # Small delay between batches to avoid overwhelming the API
            if i + batch_size < len(message_ids):
                time.sleep(0.1)

        result = {
            'success': total_success,
            'failed': total_failed,
            'skipped': total_skipped
        }

        logger.info(f"Batch labeling complete: {result}")
        return result

    def get_message_count(self, query: str = "") -> int:
        """
        Get count of messages matching query without retrieving them.

        Args:
            query: Gmail search query

        Returns:
            Number of matching messages
        """
        try:
            result = self.service.users().messages().list(
                userId=self.user_id,
                q=query,
                maxResults=1
            ).execute()

            return result.get('resultSizeEstimate', 0)

        except HttpError as e:
            logger.error(f"Failed to get message count: {e}")
            return 0

    def get_filters(self) -> List[Dict[str, Any]]:
        """
        Get all Gmail filters for the user.

        Returns:
            List of filter dictionaries
        """
        try:
            result = self.service.users().settings().filters().list(
                userId=self.user_id
            ).execute()

            filters = result.get('filter', [])
            logger.info(f"Retrieved {len(filters)} Gmail filters")
            return filters

        except HttpError as e:
            logger.error(f"Failed to get filters: {e}")
            raise GmailClientError(f"Failed to retrieve filters: {e}")

    def create_filter(self,
                     criteria: Dict[str, Any],
                     actions: Dict[str, Any]) -> str:
        """
        Create a Gmail filter with specified criteria and actions.

        Args:
            criteria: Filter criteria (from, to, subject, query, etc.)
            actions: Filter actions (addLabelIds, removeLabelIds, markAsRead, etc.)

        Returns:
            Filter ID of the created filter
        """
        try:
            filter_body = {
                'criteria': criteria,
                'action': actions
            }

            result = self.service.users().settings().filters().create(
                userId=self.user_id,
                body=filter_body
            ).execute()

            filter_id = result.get('id')
            logger.info(f"Created Gmail filter with ID: {filter_id}")
            return filter_id

        except HttpError as e:
            logger.error(f"Failed to create filter: {e}")
            raise GmailClientError(f"Failed to create filter: {e}")

    def delete_filter(self, filter_id: str) -> None:
        """
        Delete a Gmail filter by ID.

        Args:
            filter_id: Gmail filter ID to delete
        """
        try:
            self.service.users().settings().filters().delete(
                userId=self.user_id,
                id=filter_id
            ).execute()

            logger.info(f"Deleted Gmail filter: {filter_id}")

        except HttpError as e:
            logger.error(f"Failed to delete filter {filter_id}: {e}")
            raise GmailClientError(f"Failed to delete filter: {e}")

    def create_category_filters(self,
                               category_name: str,
                               category_config,
                               label_id: str) -> List[str]:
        """
        Create Gmail filters for a specific category based on rule configuration.

        Args:
            category_name: Name of the category
            category_config: CategoryConfig object with rule configuration
            label_id: Gmail label ID to apply

        Returns:
            List of created filter IDs
        """
        created_filter_ids = []

        try:
            # Create filters for high confidence domains
            high_confidence_domains = category_config.domains.get('high_confidence', [])
            if high_confidence_domains:
                for domain in high_confidence_domains:
                    criteria = {
                        'from': domain
                    }
                    actions = {
                        'addLabelIds': [label_id],
                        'markAsImportant': True
                    }

                    filter_id = self.create_filter(criteria, actions)
                    created_filter_ids.append(filter_id)
                    logger.info(f"Created filter for domain {domain} -> {category_name}")

            # Create filters for medium confidence domains (less aggressive)
            medium_confidence_domains = category_config.domains.get('medium_confidence', [])
            if medium_confidence_domains:
                for domain in medium_confidence_domains:
                    criteria = {
                        'from': domain
                    }
                    actions = {
                        'addLabelIds': [label_id]
                    }

                    filter_id = self.create_filter(criteria, actions)
                    created_filter_ids.append(filter_id)
                    logger.info(f"Created filter for domain {domain} -> {category_name}")

            # Create filters for high priority subject keywords
            subject_high_keywords = category_config.keywords.get('subject_high', [])
            if subject_high_keywords:
                # Group keywords to avoid too many filters
                keyword_groups = [subject_high_keywords[i:i+5] for i in range(0, len(subject_high_keywords), 5)]

                for group in keyword_groups:
                    # Create OR query for keywords in this group
                    subject_query = ' OR '.join([f'subject:"{keyword}"' for keyword in group])

                    criteria = {
                        'query': subject_query
                    }
                    actions = {
                        'addLabelIds': [label_id],
                        'markAsImportant': True
                    }

                    filter_id = self.create_filter(criteria, actions)
                    created_filter_ids.append(filter_id)
                    logger.info(f"Created filter for subject keywords group -> {category_name}")

            # Create filter to exclude promotional content for important categories
            exclusions = category_config.exclusions
            if exclusions and category_config.priority >= 8:
                # Create negative filter for exclusions
                exclusion_query = ' AND '.join([f'-("{exclusion}")' for exclusion in exclusions])

                # Combine with domain criteria for better precision
                if high_confidence_domains:
                    domain_query = ' OR '.join([f'from:{domain}' for domain in high_confidence_domains])
                    combined_query = f'({domain_query}) AND ({exclusion_query})'

                    criteria = {
                        'query': combined_query
                    }
                    actions = {
                        'addLabelIds': [label_id],
                        'markAsImportant': True
                    }

                    filter_id = self.create_filter(criteria, actions)
                    created_filter_ids.append(filter_id)
                    logger.info(f"Created exclusion filter for {category_name}")

            logger.info(f"Created {len(created_filter_ids)} filters for category: {category_name}")
            return created_filter_ids

        except Exception as e:
            # Clean up any created filters if there's an error
            for filter_id in created_filter_ids:
                try:
                    self.delete_filter(filter_id)
                except:
                    pass  # Ignore cleanup errors

            logger.error(f"Failed to create category filters for {category_name}: {e}")
            raise GmailClientError(f"Failed to create category filters: {e}")

    def list_filter_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all Gmail filters with readable information.

        Returns:
            Dictionary with filter summary information
        """
        try:
            filters = self.get_filters()

            summary = {
                'total_filters': len(filters),
                'filters_by_type': {
                    'domain_based': 0,
                    'subject_based': 0,
                    'query_based': 0,
                    'other': 0
                },
                'filters': []
            }

            for filter_data in filters:
                criteria = filter_data.get('criteria', {})
                actions = filter_data.get('action', {})

                # Categorize filter type
                if 'from' in criteria:
                    summary['filters_by_type']['domain_based'] += 1
                    filter_type = 'domain_based'
                elif 'subject' in criteria:
                    summary['filters_by_type']['subject_based'] += 1
                    filter_type = 'subject_based'
                elif 'query' in criteria:
                    summary['filters_by_type']['query_based'] += 1
                    filter_type = 'query_based'
                else:
                    summary['filters_by_type']['other'] += 1
                    filter_type = 'other'

                # Add readable filter info
                filter_info = {
                    'id': filter_data.get('id'),
                    'type': filter_type,
                    'criteria': criteria,
                    'actions': actions
                }
                summary['filters'].append(filter_info)

            return summary

        except Exception as e:
            logger.error(f"Failed to create filter summary: {e}")
            raise GmailClientError(f"Failed to create filter summary: {e}")

    def reset_all_filters(self, backup_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete all Gmail filters with optional backup.

        Args:
            backup_to: Optional file path to save filter backup

        Returns:
            Dictionary with reset statistics
        """
        try:
            # Get all filters for backup
            filters = self.get_filters()

            if backup_to:
                import json
                with open(backup_to, 'w') as f:
                    json.dump(filters, f, indent=2)
                logger.info(f"Filter backup saved to: {backup_to}")

            # Delete all filters
            deleted_count = 0
            failed_deletions = []

            for filter_data in filters:
                filter_id = filter_data.get('id')
                try:
                    self.delete_filter(filter_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete filter {filter_id}: {e}")
                    failed_deletions.append(filter_id)

            stats = {
                'total_filters': len(filters),
                'deleted_filters': deleted_count,
                'failed_deletions': len(failed_deletions),
                'failed_filter_ids': failed_deletions
            }

            logger.info(f"Reset complete: {deleted_count}/{len(filters)} filters deleted")
            return stats

        except Exception as e:
            logger.error(f"Failed to reset filters: {e}")
            raise GmailClientError(f"Failed to reset filters: {e}")

    def reset_category_labels(self, category_pattern: Optional[str] = None, backup_to: Optional[str] = None,
                              known_categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Delete labels matching category pattern with optional backup.

        Args:
            category_pattern: Regex pattern to match labels (default: smart category detection)
            backup_to: Optional file path to save label backup
            known_categories: List of known category names from configuration

        Returns:
            Dictionary with reset statistics
        """
        try:
            import re

            # Get all labels
            labels = self.get_labels()

            if backup_to:
                import json
                with open(backup_to, 'w') as f:
                    json.dump(labels, f, indent=2)
                logger.info(f"Label backup saved to: {backup_to}")

            # Smart category detection and pattern validation
            if not category_pattern:
                if known_categories:
                    # Create pattern to match known category names (with or without emojis)
                    category_patterns = []
                    for category in known_categories:
                        # Remove emojis and get the core name
                        core_name = re.sub(r'[^\w\s&]', '', category).strip()
                        # Match either exact category name or core name
                        escaped_category = re.escape(category)
                        escaped_core = re.escape(core_name)
                        category_patterns.append(f"^{escaped_category}$")
                        if core_name != category:
                            category_patterns.append(f"^{escaped_core}$")

                    category_pattern = '|'.join(category_patterns)
                    logger.info(f"Using smart category pattern matching for {len(known_categories)} categories")
                else:
                    # Fallback to emoji pattern
                    category_pattern = r"^[🏦🛒🔔✈️📰👤].*"
                    logger.info("Using default emoji pattern matching")
            else:
                # Convert glob-style patterns to regex
                category_pattern = self._convert_glob_to_regex(category_pattern)
                logger.info(f"Using custom pattern: {category_pattern}")

            # Validate and compile pattern
            try:
                pattern = re.compile(category_pattern, re.IGNORECASE)
            except re.error as e:
                raise GmailClientError(f"Invalid pattern '{category_pattern}': {e}")

            # Find matching labels
            matching_labels = {name: label_id for name, label_id in labels.items()
                             if pattern.match(name)}

            # Delete matching labels
            deleted_count = 0
            failed_deletions = []

            for label_name, label_id in matching_labels.items():
                try:
                    self.delete_label(label_id)
                    deleted_count += 1
                    logger.info(f"Successfully deleted label: {label_name}")
                except GmailClientError as e:
                    if "system label" in str(e).lower():
                        logger.info(f"Skipped system label (cannot delete): {label_name}")
                    else:
                        logger.warning(f"Failed to delete label {label_name}: {e}")
                        failed_deletions.append(label_name)
                except Exception as e:
                    logger.warning(f"Failed to delete label {label_name}: {e}")
                    failed_deletions.append(label_name)

            stats = {
                'total_labels': len(labels),
                'matching_labels': len(matching_labels),
                'deleted_labels': deleted_count,
                'failed_deletions': len(failed_deletions),
                'failed_label_names': failed_deletions,
                'note': f'Successfully deleted {deleted_count} labels. System labels cannot be deleted.'
            }

            logger.info(f"Label reset attempted: {len(matching_labels)} labels matched pattern")
            return stats

        except Exception as e:
            logger.error(f"Failed to reset labels: {e}")
            raise GmailClientError(f"Failed to reset labels: {e}")

    def get_reset_preview(self, include_labels: bool = True, include_filters: bool = True,
                         category_pattern: Optional[str] = None, known_categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Preview what would be reset without making changes.

        Args:
            include_labels: Include label reset preview
            include_filters: Include filter reset preview
            category_pattern: Pattern for label matching
            known_categories: List of known category names from configuration

        Returns:
            Dictionary with reset preview information
        """
        try:
            import re

            preview = {
                'labels': {},
                'filters': {},
                'warnings': []
            }

            if include_labels:
                labels = self.get_labels()

                # Smart category detection (same logic as reset_category_labels)
                if not category_pattern:
                    if known_categories:
                        category_patterns = []
                        for category in known_categories:
                            core_name = re.sub(r'[^\w\s&]', '', category).strip()
                            escaped_category = re.escape(category)
                            escaped_core = re.escape(core_name)
                            category_patterns.append(f"^{escaped_category}$")
                            if core_name != category:
                                category_patterns.append(f"^{escaped_core}$")

                        category_pattern = '|'.join(category_patterns)
                    else:
                        category_pattern = r"^[🏦🛒🔔✈️📰👤].*"
                else:
                    # Convert glob-style patterns to regex
                    category_pattern = self._convert_glob_to_regex(category_pattern)

                # Validate and compile pattern
                try:
                    pattern = re.compile(category_pattern, re.IGNORECASE)
                except re.error as e:
                    raise GmailClientError(f"Invalid pattern '{category_pattern}': {e}")

                matching_labels = {name: label_id for name, label_id in labels.items()
                                 if pattern.match(name)}

                preview['labels'] = {
                    'total_labels': len(labels),
                    'matching_labels': len(matching_labels),
                    'labels_to_reset': list(matching_labels.keys()),
                    'note': 'Labels will be permanently deleted using Gmail API (system labels will be skipped)'
                }

                if matching_labels:
                    preview['warnings'].append(
                        "Label deletion is permanent and removes labels from all messages"
                    )

            if include_filters:
                filters = self.get_filters()
                filter_summary = self.list_filter_summary()

                preview['filters'] = {
                    'total_filters': len(filters),
                    'filters_by_type': filter_summary['filters_by_type'],
                    'filters_to_delete': [f['id'] for f in filters]
                }

            return preview

        except Exception as e:
            logger.error(f"Failed to create reset preview: {e}")
            raise GmailClientError(f"Failed to create reset preview: {e}")

    def _convert_glob_to_regex(self, pattern: str) -> str:
        """
        Convert glob-style patterns to regex patterns.

        Args:
            pattern: Glob-style pattern (e.g., "Test*", "*temp*", "?est")

        Returns:
            Regex pattern string
        """
        import fnmatch
        import re

        # Handle special cases for user-friendly patterns
        if pattern == "*":
            return ".*"  # Match everything
        elif pattern == "?":
            return ".?"  # Match any single character

        # Convert glob to regex using fnmatch
        try:
            regex_pattern = fnmatch.translate(pattern)
            # fnmatch.translate adds anchors (^...$), we want partial matching
            # Remove the trailing $ to allow partial matches, keep ^ for start matching
            if regex_pattern.endswith('$'):
                regex_pattern = regex_pattern[:-1] + '.*'

            return regex_pattern
        except Exception:
            # If conversion fails, escape the pattern and treat as literal
            return re.escape(pattern)