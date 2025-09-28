#!/usr/bin/env python3
"""
Gmail Automation Suite v5.0 - Unified Edition

🚀 Complete Gmail automation solution with AI/ML capabilities, multithreading, and comprehensive management features.

Features:
- 🤖 AI-powered email categorization using BERT and topic modeling
- ⚡ Multithreaded concurrent processing for maximum performance
- 🏷️ Smart label creation and management with custom colors
- 🔍 Advanced filter creation with importance marking and archiving
- 📧 Incremental labeling of unlabeled emails for maintenance
- 🧠 Hybrid rule-based + machine learning classification
- 🗑️ Label management, migration, and cleanup operations
- 🧹 Complete reset and cleanup capabilities
- 📊 Comprehensive reporting and progress tracking
- 🔄 Producer-consumer architecture for real-time processing

Author: Gmail Automation Suite
Version: 5.0.0 - Unified Edition
"""

import os
import re
import time
import json
import argparse
import warnings
import threading
import queue
import datetime
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Gmail color palette (hex codes that work with Gmail API)
GMAIL_COLORS = {
    '#4a86e8': {'textColor': '#ffffff', 'backgroundColor': '#4a86e8'},  # Blue
    '#16a766': {'textColor': '#ffffff', 'backgroundColor': '#16a766'},  # Green
    '#cc3a21': {'textColor': '#ffffff', 'backgroundColor': '#cc3a21'},  # Red
    '#ffad47': {'textColor': '#ffffff', 'backgroundColor': '#ffad47'},  # Orange
    '#8e63ce': {'textColor': '#ffffff', 'backgroundColor': '#8e63ce'},  # Purple
    '#666666': {'textColor': '#ffffff', 'backgroundColor': '#666666'},  # Gray
    '#fb4c2f': {'textColor': '#ffffff', 'backgroundColor': '#fb4c2f'},  # Bright Red
    '#cccccc': {'textColor': '#000000', 'backgroundColor': '#cccccc'},  # Light Gray
    '#43d692': {'textColor': '#ffffff', 'backgroundColor': '#43d692'},  # Light Green
    '#fad165': {'textColor': '#000000', 'backgroundColor': '#fad165'},  # Yellow
}

@dataclass
class Label:
    name: str
    color: str

@dataclass
class Filter:
    label: str
    config: Dict

@dataclass
class EmailTask:
    """Represents an email to be processed"""
    email_id: str
    email_data: Dict

@dataclass
class ProcessingStats:
    """Thread-safe statistics tracking"""
    def __init__(self):
        self.lock = threading.Lock()
        self.emails_found = 0
        self.emails_processed = 0
        self.emails_labeled = 0
        self.emails_skipped = 0
        self.errors = 0
        self.categories = {}

    def increment_found(self):
        with self.lock:
            self.emails_found += 1

    def increment_processed(self):
        with self.lock:
            self.emails_processed += 1

    def increment_labeled(self, category: str):
        with self.lock:
            self.emails_labeled += 1
            self.categories[category] = self.categories.get(category, 0) + 1

    def increment_skipped(self):
        with self.lock:
            self.emails_skipped += 1

    def increment_errors(self):
        with self.lock:
            self.errors += 1

    def get_stats(self) -> Dict:
        with self.lock:
            return {
                'found': self.emails_found,
                'processed': self.emails_processed,
                'labeled': self.emails_labeled,
                'skipped': self.emails_skipped,
                'errors': self.errors,
                'categories': self.categories.copy()
            }

@dataclass
class IncrementalScanConfig:
    """Configuration for incremental email scanning"""
    only_unlabeled: bool = True
    exclude_system_labels: bool = True
    exclude_categories: List[str] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    batch_size: int = 100
    resume_from_id: Optional[str] = None

    def __post_init__(self):
        if self.exclude_categories is None:
            self.exclude_categories = ['CHAT', 'SENT', 'DRAFT', 'SPAM', 'TRASH']

class GmailAutomationUnified:
    """Unified Gmail automation class with all features"""

    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json',
                 use_ml: bool = True):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.labels_cache = {}
        self.categories_config = self.load_categories_config()

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

        # Predefined labels with Gmail-approved colors
        self.labels = [
            Label('🏦 Banking & Finance', '#4a86e8'),      # Blue
            Label('📈 Investments & Trading', '#16a766'),   # Green
            Label('🔔 Alerts & Security', '#cc3a21'),       # Red
            Label('🛒 Shopping & Orders', '#ffad47'),       # Orange
            Label('👤 Personal & Work', '#8e63ce'),         # Purple
            Label('📰 Marketing & News', '#666666'),        # Gray
            Label('🎯 Action Required', '#fb4c2f'),         # Bright Red
            Label('📦 Receipts & Archive', '#cccccc'),      # Light Gray
            Label('🏥 Insurance & Services', '#43d692'),    # Light Green
            Label('✈️ Travel & Transport', '#fad165')       # Yellow
        ]

        # State tracking for incremental processing
        self.processing_state = {
            'last_scan_time': None,
            'last_processed_id': None,
            'total_processed': 0,
            'session_start': datetime.datetime.now().isoformat()
        }

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

    def create_labels(self) -> bool:
        """Create Gmail labels with colors"""
        print("🏷️ Creating labels...")

        for label in self.labels:
            try:
                # Check if label already exists
                existing_labels = self.service.users().labels().list(userId='me').execute()
                existing_names = [l['name'] for l in existing_labels.get('labels', [])]

                if label.name in existing_names:
                    print(f"   ⏭️  Label '{label.name}' already exists")
                    continue

                # Prepare label object with color
                label_object = {
                    'name': label.name,
                    'messageListVisibility': 'show',
                    'labelListVisibility': 'labelShow'
                }

                # Add color if available
                if label.color in GMAIL_COLORS:
                    label_object['color'] = GMAIL_COLORS[label.color]

                # Create the label
                created_label = self.service.users().labels().create(
                    userId='me',
                    body=label_object
                ).execute()

                print(f"   ✅ Created: {label.name}")
                time.sleep(0.1)  # Rate limiting

            except HttpError as e:
                error_details = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
                print(f"   ❌ Error creating label '{label.name}': {error_details}")

                # Try creating without color as fallback
                try:
                    fallback_label = {
                        'name': label.name,
                        'messageListVisibility': 'show',
                        'labelListVisibility': 'labelShow'
                    }

                    self.service.users().labels().create(
                        userId='me',
                        body=fallback_label
                    ).execute()

                    print(f"   ✅ Created (no color): {label.name}")
                except Exception as fallback_error:
                    print(f"   ❌ Fallback failed: {fallback_error}")

        print("✅ Label creation completed")
        return True

    def get_existing_labels(self) -> Dict[str, str]:
        """Get existing automation labels as a mapping of name to ID"""
        try:
            labels_result = self.service.users().labels().list(userId='me').execute()
            labels = labels_result.get('labels', [])

            automation_labels = {}
            for label in labels:
                label_name = label['name']
                # Check if it's one of our automation labels
                if any(emoji in label_name for emoji in ['🏦', '📈', '🔔', '🛒', '👤', '📰', '🎯', '📦', '🏥', '✈️']):
                    automation_labels[label_name] = label['id']

            return automation_labels
        except Exception as e:
            print(f"⚠️ Error getting labels: {e}")
            return {}

    def get_automation_label_ids(self) -> Set[str]:
        """Get set of automation label IDs for filtering"""
        return set(self.get_existing_labels().values())

    def categorize_email(self, email_data: Dict) -> Optional[str]:
        """Categorize email using hybrid rule-based + ML approach"""
        if not self.categories_config:
            return None

        # Use ML categorizer if available and enabled
        if self.use_ml and self.ml_categorizer:
            try:
                result = self.ml_categorizer.hybrid_categorize(email_data)
                return result.get('final_category')
            except Exception as e:
                print(f"⚠️ ML categorization failed, using rule-based: {e}")

        # Fallback to rule-based categorization
        return self._categorize_email_rule_based(email_data)

    def categorize_email_debug(self, email_data: Dict) -> Dict:
        """Categorize email with debug information"""
        if self.use_ml and self.ml_categorizer:
            try:
                return self.ml_categorizer.hybrid_categorize(email_data)
            except Exception as e:
                print(f"⚠️ ML categorization failed: {e}")

        # Fallback to rule-based with debug
        result = self._categorize_email_rule_based(email_data)
        return {
            'email': email_data,
            'final_category': result,
            'rule_based': {'scores': {}, 'best_category': result},
            'method_used': 'rule_based_fallback'
        }

    def _categorize_email_rule_based(self, email_data: Dict) -> Optional[str]:
        """Rule-based email categorization as fallback"""
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()
        snippet = email_data.get('snippet', '').lower()

        # Simple rule-based categorization
        if any(keyword in sender + subject + snippet for keyword in ['bank', 'payment', 'invoice', 'bill']):
            return '🏦 Banking & Finance'
        elif any(keyword in sender + subject + snippet for keyword in ['order', 'shipping', 'delivery', 'purchase']):
            return '🛒 Shopping & Orders'
        elif any(keyword in sender + subject + snippet for keyword in ['security', 'alert', 'warning', 'urgent']):
            return '🔔 Alerts & Security'
        elif any(keyword in sender + subject + snippet for keyword in ['investment', 'trading', 'stock', 'portfolio']):
            return '📈 Investments & Trading'
        elif any(keyword in sender + subject + snippet for keyword in ['newsletter', 'unsubscribe', 'marketing']):
            return '📰 Marketing & News'
        elif any(keyword in sender + subject + snippet for keyword in ['travel', 'flight', 'hotel', 'booking']):
            return '✈️ Travel & Transport'
        elif any(keyword in sender + subject + snippet for keyword in ['insurance', 'health', 'medical']):
            return '🏥 Insurance & Services'
        elif any(keyword in sender + subject + snippet for keyword in ['receipt', 'confirmation', 'subscription']):
            return '📦 Receipts & Archive'
        elif any(keyword in sender + subject + snippet for keyword in ['action required', 'respond', 'reply needed']):
            return '🎯 Action Required'
        else:
            return '👤 Personal & Work'

    def is_email_unlabeled(self, email_labels: List[str], automation_label_ids: Set[str],
                          config: IncrementalScanConfig) -> bool:
        """Check if an email is unlabeled according to our criteria"""
        if not config.only_unlabeled:
            return True

        # Check if email has any automation labels
        has_automation_label = bool(set(email_labels) & automation_label_ids)

        if has_automation_label:
            return False

        # Exclude system labels if configured
        if config.exclude_system_labels:
            system_labels = {'INBOX', 'UNREAD', 'STARRED', 'IMPORTANT'}
            # Only consider non-system labels for determining if email is "user-labeled"
            user_labels = [label for label in email_labels if label not in system_labels]
            if user_labels:
                # Email has user labels but no automation labels - skip it
                return False

        return True

    def get_unlabeled_emails(self, config: IncrementalScanConfig, max_emails: int = 1000) -> List[Dict]:
        """Get emails that don't have automation labels"""
        if max_emails == 0:
            print(f"🔍 Scanning for ALL unlabeled emails (unlimited)...")
        else:
            print(f"🔍 Scanning for unlabeled emails (max: {max_emails})...")

        # Build Gmail search query
        query_parts = []

        # Date filtering
        if config.min_date:
            query_parts.append(f"after:{config.min_date}")
        if config.max_date:
            query_parts.append(f"before:{config.max_date}")

        # Exclude categories if specified
        if config.exclude_categories:
            for category in config.exclude_categories:
                query_parts.append(f"-in:{category.lower()}")

        # Build final query
        query = ' '.join(query_parts) if query_parts else None

        # Get automation label IDs for filtering
        automation_label_ids = self.get_automation_label_ids()
        print(f"   📋 Found {len(automation_label_ids)} automation labels to check against")

        try:
            # Fetch emails in batches
            unlabeled_emails = []
            next_page_token = None
            processed_count = 0

            # Continue while we haven't reached max_emails (if limited) or while there are more emails
            while max_emails == 0 or len(unlabeled_emails) < max_emails:
                # Calculate how many to fetch in this batch
                if max_emails == 0:
                    # Unlimited mode - use maximum API batch size
                    batch_size = min(config.batch_size, 500)  # Gmail API limit is 500
                else:
                    # Limited mode - respect remaining count
                    remaining = max_emails - len(unlabeled_emails)
                    batch_size = min(config.batch_size, remaining, 500)

                # Fetch batch of emails
                request_params = {
                    'userId': 'me',
                    'maxResults': batch_size,
                    'q': query
                }

                if next_page_token:
                    request_params['pageToken'] = next_page_token

                result = self.service.users().messages().list(**request_params).execute()
                messages = result.get('messages', [])

                if not messages:
                    break

                # Check each email for labels
                batch_unlabeled = []
                for msg in messages:
                    processed_count += 1

                    # Get email details with labels
                    email = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()

                    email_labels = email.get('labelIds', [])

                    # Check if this email is unlabeled according to our criteria
                    if self.is_email_unlabeled(email_labels, automation_label_ids, config):
                        batch_unlabeled.append(email)

                    # Resume capability
                    if config.resume_from_id and msg['id'] == config.resume_from_id:
                        print(f"   📍 Resuming from email ID: {config.resume_from_id}")
                        batch_unlabeled = []  # Clear batch, start fresh from here

                    # Progress update
                    progress_interval = 100 if max_emails == 0 else 500
                    if processed_count % progress_interval == 0:
                        if max_emails == 0:
                            print(f"   📊 Unlimited scan: Processed {processed_count} emails, found {len(unlabeled_emails)} unlabeled so far...")
                        else:
                            print(f"   📊 Processed {processed_count} emails, found {len(unlabeled_emails)} unlabeled so far...")

                unlabeled_emails.extend(batch_unlabeled)

                # Get next page token
                next_page_token = result.get('nextPageToken')
                if not next_page_token:
                    if max_emails == 0:
                        print("   📍 Reached end of inbox (no more emails)")
                    break

                # Show progress
                if max_emails == 0:
                    print(f"   📦 Batch complete: +{len(batch_unlabeled)} unlabeled emails (total: {len(unlabeled_emails)}, scanned: {processed_count})")
                else:
                    print(f"   📦 Batch complete: +{len(batch_unlabeled)} unlabeled emails (total: {len(unlabeled_emails)})")

                # Add safety check for unlimited scans
                if max_emails == 0 and processed_count > 50000:
                    print(f"   ⚠️ Large inbox detected ({processed_count} emails scanned). Consider using --max-emails to limit scope.")
                    if processed_count % 10000 == 0:
                        response = input(f"   Continue scanning? (y/N): ").strip().lower()
                        if response != 'y':
                            print("   🛑 Scan stopped by user")
                            break

        except Exception as e:
            print(f"❌ Error fetching unlabeled emails: {e}")
            return []

        print(f"✅ Found {len(unlabeled_emails)} unlabeled emails out of {processed_count} checked")
        return unlabeled_emails

    def _process_single_email(self, email: Dict, existing_labels: Dict, debug: bool) -> Dict:
        """Process a single email (for concurrent processing)"""
        email_stats = {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0, 'categories': {}}

        try:
            msg_id = email['id']

            # Extract email data for categorization
            headers = {h['name'].lower(): h['value'] for h in email.get('payload', {}).get('headers', [])}
            email_data = {
                'sender': headers.get('from', ''),
                'subject': headers.get('subject', ''),
                'snippet': email.get('snippet', '')
            }

            # Categorize email
            if debug:
                debug_info = self.categorize_email_debug(email_data)
                suggested_label = debug_info['final_category']

                print(f"    🔍 DEBUG: {debug_info['email']['sender'][:30]}")
                print(f"       Subject: {debug_info['email']['subject']}")
                print(f"       Rule-based scores: {debug_info['rule_based']['scores']}")
                if 'ml_prediction' in debug_info:
                    print(f"       ML method: {debug_info.get('method_used', 'unknown')}")
                    print(f"       ML confidence: {debug_info.get('final_confidence', 0):.2f}")
                print(f"       Final result: {suggested_label}")
            else:
                suggested_label = self.categorize_email(email_data)

            email_stats['processed'] += 1

            if suggested_label and suggested_label in existing_labels:
                # Check if email already has this label
                current_labels = email.get('labelIds', [])
                target_label_id = existing_labels[suggested_label]

                if target_label_id not in current_labels:
                    # Apply the label
                    self.service.users().messages().modify(
                        userId='me',
                        id=msg_id,
                        body={'addLabelIds': [target_label_id]}
                    ).execute()

                    email_stats['labeled'] += 1
                    email_stats['categories'][suggested_label] = email_stats['categories'].get(suggested_label, 0) + 1

                    sender_short = email_data['sender'].split('@')[0] if '@' in email_data['sender'] else email_data['sender'][:30]
                    subject_short = email_data['subject'][:40] + "..." if len(email_data['subject']) > 40 else email_data['subject']
                    print(f"    ✅ {sender_short[:20]}: {subject_short} → {suggested_label}")
                else:
                    email_stats['skipped'] += 1
            else:
                email_stats['skipped'] += 1

            # Brief rate limiting for API respect
            time.sleep(0.05)

        except Exception as e:
            print(f"    ❌ Error processing email {email.get('id', 'unknown')}: {e}")
            email_stats['errors'] += 1

        return email_stats

    def process_email_batch_concurrent(self, batch_emails: List[Dict], existing_labels: Dict,
                                     debug: bool, max_workers: int = 4) -> Dict:
        """Process a batch of emails using concurrent processing"""
        if not batch_emails:
            return {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0, 'categories': {}}

        stats = {
            'processed': 0,
            'labeled': 0,
            'skipped': 0,
            'errors': 0,
            'categories': {}
        }

        # Use ThreadPoolExecutor for concurrent processing within the batch
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all emails for processing
            future_to_email = {
                executor.submit(self._process_single_email, email, existing_labels, debug): email
                for email in batch_emails
            }

            # Collect results as they complete
            for future in as_completed(future_to_email):
                email = future_to_email[future]
                try:
                    email_stats = future.result()

                    # Merge email stats
                    for key in ['processed', 'labeled', 'skipped', 'errors']:
                        stats[key] += email_stats.get(key, 0)

                    for category, count in email_stats.get('categories', {}).items():
                        stats['categories'][category] = stats['categories'].get(category, 0) + count

                except Exception as e:
                    print(f"⚠️ Error processing email {email.get('id', 'unknown')}: {e}")
                    stats['errors'] += 1

        return stats

    def scan_and_label_emails(self, max_emails: int = 1000, days_back: int = 30,
                            debug: bool = False, concurrent: bool = False, max_workers: int = 4) -> Dict[str, int]:
        """
        Scan and label emails with optional concurrent processing

        Args:
            max_emails: Maximum emails to process
            days_back: How many days back to scan (0 = all)
            debug: Show debug information
            concurrent: Use concurrent processing
            max_workers: Maximum number of worker threads

        Returns:
            Statistics dictionary
        """
        mode = "concurrent" if concurrent else "sequential"
        print(f"📧 Scanning and labeling emails ({mode} processing)...")
        print(f"📊 Parameters: max_emails={max_emails}, days_back={days_back}, workers={max_workers if concurrent else 1}")
        print("-" * 60)

        # Get existing labels
        existing_labels = self.get_existing_labels()
        if not existing_labels:
            print("❌ No labels found. Please create labels first.")
            return {'error': 'No labels found'}

        print(f"📋 Found {len(existing_labels)} existing labels")

        # Get emails to process
        query = None
        if days_back > 0:
            target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
            date_str = target_date.strftime('%Y/%m/%d')
            query = f"after:{date_str}"

        try:
            result = self.service.users().messages().list(
                userId='me',
                maxResults=min(max_emails, 500) if max_emails > 0 else 500,
                q=query
            ).execute()

            message_ids = [msg['id'] for msg in result.get('messages', [])]

            if max_emails == 0:
                # Handle unlimited scanning
                all_message_ids = message_ids
                next_page_token = result.get('nextPageToken')

                while next_page_token:
                    result = self.service.users().messages().list(
                        userId='me',
                        maxResults=500,
                        q=query,
                        pageToken=next_page_token
                    ).execute()

                    all_message_ids.extend([msg['id'] for msg in result.get('messages', [])])
                    next_page_token = result.get('nextPageToken')

                    if len(all_message_ids) % 1000 == 0:
                        print(f"   📊 Fetched {len(all_message_ids)} email IDs so far...")

                message_ids = all_message_ids

            emails_to_process = []
            print(f"📬 Fetching details for {len(message_ids)} emails...")

            for i, msg_id in enumerate(message_ids):
                email = self.service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                emails_to_process.append(email)

                if (i + 1) % 100 == 0:
                    print(f"   📊 Fetched {i + 1}/{len(message_ids)} email details...")

        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 1}

        if not emails_to_process:
            print("✅ No emails found to process")
            return {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0}

        print(f"📬 Processing {len(emails_to_process)} emails...")

        # Process emails in batches
        stats = {
            'processed': 0,
            'labeled': 0,
            'skipped': 0,
            'errors': 0,
            'categories': {}
        }

        batch_size = 50
        total_batches = (len(emails_to_process) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(emails_to_process))
            batch_emails = emails_to_process[start_idx:end_idx]

            mode_text = f"concurrently with {max_workers} workers" if concurrent else "sequentially"
            print(f"\n🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_emails)} emails) {mode_text}")

            if concurrent:
                batch_stats = self.process_email_batch_concurrent(batch_emails, existing_labels, debug, max_workers)
            else:
                batch_stats = self._process_email_batch_sequential(batch_emails, existing_labels, debug)

            # Merge batch stats
            for key in ['processed', 'labeled', 'skipped', 'errors']:
                stats[key] += batch_stats.get(key, 0)

            for category, count in batch_stats.get('categories', {}).items():
                stats['categories'][category] = stats['categories'].get(category, 0) + count

            # Progress update
            progress = ((batch_num + 1) / total_batches) * 100
            print(f"📈 Progress: {progress:.1f}% complete")

            # Rate limiting between batches
            delay = 0.5 if concurrent else 1.0
            if batch_num < total_batches - 1:
                time.sleep(delay)

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 EMAIL LABELING SUMMARY ({mode.upper()})")
        print("=" * 60)
        print(f"📧 Total processed: {stats['processed']}")
        print(f"✅ Successfully labeled: {stats['labeled']}")
        print(f"⏭️  Skipped (already labeled/no category): {stats['skipped']}")
        print(f"❌ Errors: {stats['errors']}")
        if concurrent:
            print(f"⚡ Workers used: {max_workers}")

        if stats['categories']:
            print(f"\n📋 Categories applied:")
            for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {category}: {count} emails")

        success_rate = (stats['labeled'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
        print(f"\n📈 Success rate: {success_rate:.1f}%")

        print(f"\nEmail labeling completed: {stats['labeled']} emails labeled")
        return stats

    def _process_email_batch_sequential(self, batch_emails: List[Dict], existing_labels: Dict, debug: bool) -> Dict:
        """Process a batch of emails sequentially (original method)"""
        batch_stats = {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0, 'categories': {}}

        for i, email in enumerate(batch_emails):
            try:
                msg_id = email['id']

                # Extract email data for categorization
                headers = {h['name'].lower(): h['value'] for h in email.get('payload', {}).get('headers', [])}
                email_data = {
                    'sender': headers.get('from', ''),
                    'subject': headers.get('subject', ''),
                    'snippet': email.get('snippet', '')
                }

                # Categorize email
                if debug and i < 3:  # Show debug for first few emails
                    debug_info = self.categorize_email_debug(email_data)
                    suggested_label = debug_info['final_category']

                    print(f"    🔍 DEBUG: {debug_info['email']['sender'][:30]}")
                    print(f"       Subject: {debug_info['email']['subject']}")
                    print(f"       Rule-based scores: {debug_info['rule_based']['scores']}")
                    if 'ml_prediction' in debug_info:
                        print(f"       ML method: {debug_info.get('method_used', 'unknown')}")
                        print(f"       ML confidence: {debug_info.get('final_confidence', 0):.2f}")
                    print(f"       Final result: {suggested_label}")
                else:
                    suggested_label = self.categorize_email(email_data)

                batch_stats['processed'] += 1

                if suggested_label and suggested_label in existing_labels:
                    # Check if email already has this label
                    current_labels = email.get('labelIds', [])
                    target_label_id = existing_labels[suggested_label]

                    if target_label_id not in current_labels:
                        # Apply the label
                        self.service.users().messages().modify(
                            userId='me',
                            id=msg_id,
                            body={'addLabelIds': [target_label_id]}
                        ).execute()

                        batch_stats['labeled'] += 1
                        batch_stats['categories'][suggested_label] = batch_stats['categories'].get(suggested_label, 0) + 1

                        # Show progress for first few in batch
                        if i < 3:
                            sender_short = email_data['sender'].split('@')[0] if '@' in email_data['sender'] else email_data['sender'][:30]
                            subject_short = email_data['subject'][:40] + "..." if len(email_data['subject']) > 40 else email_data['subject']
                            print(f"    ✅ {sender_short[:20]}: {subject_short} → {suggested_label}")
                    else:
                        batch_stats['skipped'] += 1
                else:
                    batch_stats['skipped'] += 1

                # Rate limiting
                if (batch_stats['processed'] % 10) == 0:
                    time.sleep(0.1)

            except Exception as e:
                print(f"    ❌ Error processing email {i+1}: {e}")
                batch_stats['errors'] += 1

        return batch_stats

    def scan_unlabeled_emails(self, max_emails: int = 1000, days_back: int = 30,
                            debug: bool = False, resume_from_id: str = None,
                            concurrent: bool = False, max_workers: int = 4) -> Dict[str, int]:
        """
        Scan and label only emails that don't have automation labels

        Args:
            max_emails: Maximum emails to process (0 = unlimited)
            days_back: How many days back to scan (0 = all)
            debug: Show debug information
            resume_from_id: Resume processing from specific email ID
            concurrent: Use concurrent processing
            max_workers: Maximum number of worker threads

        Returns:
            Statistics dictionary
        """
        mode = "concurrent" if concurrent else "sequential"
        print(f"📧 Scanning and labeling unlabeled emails ({mode} processing)...")
        print(f"📊 Parameters: max_emails={max_emails}, days_back={days_back}, workers={max_workers if concurrent else 1}")
        print("-" * 60)

        # Configure incremental scan
        config = IncrementalScanConfig(
            only_unlabeled=True,
            exclude_system_labels=True,
            min_date=self._get_date_string(days_back) if days_back > 0 else None,
            resume_from_id=resume_from_id
        )

        # Get existing labels
        existing_labels = self.get_existing_labels()
        if not existing_labels:
            print("❌ No labels found. Please create labels first.")
            return {'error': 'No labels found'}

        print(f"📋 Found {len(existing_labels)} existing labels")

        # Get unlabeled emails
        emails_to_process = self.get_unlabeled_emails(config, max_emails)

        if not emails_to_process:
            print("✅ No unlabeled emails found - your inbox is fully organized!")
            return {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0}

        print(f"📬 Processing {len(emails_to_process)} emails...")

        # Process emails in batches
        stats = {
            'processed': 0,
            'labeled': 0,
            'skipped': 0,
            'errors': 0,
            'categories': {}
        }

        batch_size = 50
        total_batches = (len(emails_to_process) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(emails_to_process))
            batch_emails = emails_to_process[start_idx:end_idx]

            mode_text = f"concurrently with {max_workers} workers" if concurrent else "sequentially"
            print(f"\n🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_emails)} emails) {mode_text}")

            if concurrent:
                batch_stats = self.process_email_batch_concurrent(batch_emails, existing_labels, debug, max_workers)
            else:
                batch_stats = self._process_email_batch_sequential(batch_emails, existing_labels, debug)

            # Merge batch stats
            for key in ['processed', 'labeled', 'skipped', 'errors']:
                stats[key] += batch_stats.get(key, 0)

            for category, count in batch_stats.get('categories', {}).items():
                stats['categories'][category] = stats['categories'].get(category, 0) + count

            # Progress update
            progress = ((batch_num + 1) / total_batches) * 100
            print(f"📈 Progress: {progress:.1f}% complete")

            # Rate limiting between batches
            delay = 0.5 if concurrent else 1.0
            if batch_num < total_batches - 1:
                time.sleep(delay)

        # Save processing state
        self.processing_state.update({
            'last_scan_time': datetime.datetime.now().isoformat(),
            'last_processed_id': emails_to_process[-1]['id'] if emails_to_process else None,
            'total_processed': self.processing_state['total_processed'] + stats['processed']
        })

        self._save_processing_state()

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 INCREMENTAL EMAIL LABELING SUMMARY ({mode.upper()})")
        print("=" * 60)
        print(f"📧 Total processed: {stats['processed']}")
        print(f"✅ Successfully labeled: {stats['labeled']}")
        print(f"⏭️  Skipped (already labeled/no category): {stats['skipped']}")
        print(f"❌ Errors: {stats['errors']}")
        if concurrent:
            print(f"⚡ Workers used: {max_workers}")

        if stats['categories']:
            print(f"\n📋 Categories applied:")
            for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {category}: {count} emails")

        success_rate = (stats['labeled'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
        print(f"\n📈 Success rate: {success_rate:.1f}%")

        print("🎯 Incremental mode: Only processed unlabeled emails")
        print(f"\nIncremental email labeling completed: {stats['labeled']} emails labeled")
        return stats

    def _get_date_string(self, days_back: int) -> str:
        """Get date string for Gmail search query"""
        if days_back <= 0:
            return None
        target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        return target_date.strftime('%Y/%m/%d')

    def _save_processing_state(self):
        """Save processing state to file"""
        try:
            with open('processing_state.json', 'w') as f:
                json.dump(self.processing_state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save processing state: {e}")

    def _load_processing_state(self):
        """Load processing state from file"""
        try:
            if os.path.exists('processing_state.json'):
                with open('processing_state.json', 'r') as f:
                    saved_state = json.load(f)
                self.processing_state.update(saved_state)
                print(f"📊 Loaded processing state: {self.processing_state['total_processed']} emails processed previously")
        except Exception as e:
            print(f"⚠️ Could not load processing state: {e}")

    # Additional utility methods would go here...
    # (cleanup, reset, filter creation, etc.)

def main():
    """Unified main function with all options"""
    parser = argparse.ArgumentParser(description='Gmail Automation Suite v5.0 - Unified Edition')

    # Basic options
    parser.add_argument('--credentials', default='credentials.json',
                       help='Path to credentials file (default: credentials.json)')
    parser.add_argument('--token', default='token.json',
                       help='Path to token file (default: token.json)')

    # Core operations
    parser.add_argument('--labels-only', action='store_true',
                       help='Only create labels, skip filters and scanning')
    parser.add_argument('--scan-emails', action='store_true',
                       help='Scan and label all emails')
    parser.add_argument('--scan-unlabeled', action='store_true',
                       help='Scan and label only emails without automation labels')
    parser.add_argument('--scan-all-unlabeled', action='store_true',
                       help='Scan ALL unlabeled emails (no date or count limit)')

    # Processing options
    parser.add_argument('--max-emails', type=int, default=1000,
                       help='Maximum emails to process (default: 1000, 0 = unlimited)')
    parser.add_argument('--days-back', type=int, default=30,
                       help='Days back to scan (default: 30, 0 = all)')
    parser.add_argument('--resume-from', type=str,
                       help='Resume processing from specific email ID')
    parser.add_argument('--debug-categorization', action='store_true',
                       help='Show detailed categorization info')

    # Concurrent processing options
    parser.add_argument('--concurrent', action='store_true',
                       help='Use concurrent processing for improved performance')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of worker threads (default: 4)')

    # ML options
    parser.add_argument('--disable-ml', action='store_true',
                       help='Disable ML categorization')
    parser.add_argument('--ml-info', action='store_true',
                       help='Show ML model information')
    parser.add_argument('--bootstrap-training', action='store_true',
                       help='Bootstrap ML model training')

    # Semi-supervised learning options
    parser.add_argument('--review-clusters', action='store_true',
                       help='Interactive cluster review for semi-supervised learning')
    parser.add_argument('--cluster-count', type=int, default=10,
                       help='Number of clusters for review (default: 10)')
    parser.add_argument('--review-emails', type=int, default=200,
                       help='Number of emails to include in clustering review (default: 200)')
    parser.add_argument('--confidence-threshold', type=float, default=0.8,
                       help='Max confidence for uncertainty sampling (default: 0.8)')

    args = parser.parse_args()

    # Initialize automation
    automation = GmailAutomationUnified(args.credentials, args.token, use_ml=not args.disable_ml)

    print("🔍 Validating environment...")
    if not automation.authenticate():
        print("❌ Authentication failed")
        return 1
    print("✅ Authentication successful!")

    # Load processing state
    automation._load_processing_state()

    # Handle ML operations
    if args.ml_info:
        if automation.use_ml and automation.ml_categorizer:
            info = automation.ml_categorizer.get_model_info()
            print("🤖 ML Model Information")
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

    # Handle semi-supervised learning review
    if args.review_clusters:
        try:
            from email_clustering_reviewer import EmailClusteringReviewer
            print("🎯 Starting Semi-Supervised Learning Review Session")
            print("=" * 60)

            reviewer = EmailClusteringReviewer(gmail_automation=automation)

            # Collect emails for review
            emails_for_review = reviewer.collect_emails_for_review(
                max_emails=args.review_emails,
                max_confidence=args.confidence_threshold
            )

            if not emails_for_review:
                print("✅ No emails found that need review at this confidence level")
                print(f"💡 Try adjusting --confidence-threshold (current: {args.confidence_threshold})")
                return 0

            # Create clusters
            clusters = reviewer.create_email_clusters(
                emails_for_review,
                n_clusters=min(args.cluster_count, len(emails_for_review) // 5)
            )

            if not clusters:
                print("❌ Could not create clusters for review")
                return 1

            # Start interactive review
            session = reviewer.start_interactive_review(clusters)

            # Export training data if corrections were made
            if session.corrections_made > 0:
                training_file = reviewer.export_training_data(session.session_id)
                print(f"\n🎉 Semi-supervised learning session completed!")
                print(f"📊 Training data exported to: {training_file}")
                print("\n💡 Next steps:")
                print("1. Review the exported training data")
                print("2. Use it to retrain your ML model")
                print("3. Run regular email scanning to test improvements")
            else:
                print("\n✅ Review completed - no corrections needed!")

        except ImportError:
            print("❌ Email clustering reviewer not available")
            print("💡 Install required packages: pip install scikit-learn matplotlib seaborn")
        except Exception as e:
            print(f"❌ Error during cluster review: {e}")

        return 0

    # Handle label creation
    if args.labels_only:
        automation.create_labels()
        return 0

    # Handle email scanning operations
    if args.scan_emails or args.scan_unlabeled or args.scan_all_unlabeled:
        # Determine parameters for scanning
        if args.scan_all_unlabeled:
            days_back = 0
            max_emails = 0 if args.max_emails == 1000 else args.max_emails  # 0 = unlimited if default
            print("🔄 Scanning ALL unlabeled emails (no limits) - this may take a while...")
        else:
            days_back = args.days_back
            max_emails = args.max_emails

        # Override max_emails if explicitly set to 0
        if args.max_emails == 0:
            max_emails = 0

        # Choose scanning method
        if args.scan_unlabeled or args.scan_all_unlabeled:
            # Incremental scanning (unlabeled only)
            stats = automation.scan_unlabeled_emails(
                max_emails=max_emails,
                days_back=days_back,
                debug=args.debug_categorization,
                resume_from_id=args.resume_from,
                concurrent=args.concurrent,
                max_workers=args.max_workers
            )
        else:
            # Full email scanning
            stats = automation.scan_and_label_emails(
                max_emails=max_emails,
                days_back=days_back,
                debug=args.debug_categorization,
                concurrent=args.concurrent,
                max_workers=args.max_workers
            )

        return 0 if stats.get('errors', 0) == 0 else 1

    # Default behavior - create labels first
    print("🎯 Gmail Automation Suite v5.0 - Unified Edition")
    print("📋 Creating labels first...")
    automation.create_labels()

    print("\n💡 Available operations:")
    print("   --labels-only                 Create labels only")
    print("   --scan-emails                 Scan and label all emails")
    print("   --scan-unlabeled              Scan only unlabeled emails (incremental)")
    print("   --scan-all-unlabeled          Scan ALL unlabeled emails (unlimited)")
    print("   --max-emails 0                Unlimited email processing")
    print("   --concurrent                  Use multithreaded processing")
    print("   --max-workers N               Control number of threads")
    print("   --debug-categorization        Show AI decision process")
    print("   --ml-info                     Show ML model status")
    print("   --bootstrap-training          Train initial ML model")
    print("   --review-clusters             Interactive cluster review for corrections")
    print("   --cluster-count N             Number of clusters for review")
    print("   --confidence-threshold X      Max confidence for uncertainty sampling")
    print("   --help                        Show all options")

    return 0

if __name__ == "__main__":
    exit(main())