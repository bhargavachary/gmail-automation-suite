#!/usr/bin/env python3
"""
Gmail Automation Suite v4.1 - Extended with Incremental Labeling

Enhanced version with intelligent incremental labeling features:
- Scan only unlabeled emails for efficiency
- Periodic maintenance mode
- Smart batch processing with resume capability
- Advanced filtering for new emails only
- Enhanced reporting and statistics

Author: Gmail Automation Suite
Version: 4.1.0 - Extended Edition
"""

import os
import re
import time
import json
import argparse
import warnings
import datetime
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
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

class GmailAutomationExtended:
    """Extended Gmail automation class with incremental labeling capabilities"""

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

    def is_email_unlabeled(self, email_labels: List[str], automation_label_ids: Set[str],
                          config: IncrementalScanConfig) -> bool:
        """
        Check if an email is unlabeled according to our criteria

        Args:
            email_labels: List of label IDs on the email
            automation_label_ids: Set of our automation label IDs
            config: Incremental scan configuration

        Returns:
            True if email should be processed (is unlabeled)
        """
        if not config.only_unlabeled:
            return True

        # Check if email has any of our automation labels
        has_automation_label = bool(automation_label_ids.intersection(set(email_labels)))
        if has_automation_label:
            return False

        # Check if email has system labels we want to exclude
        if config.exclude_system_labels:
            system_labels = {'INBOX', 'UNREAD', 'IMPORTANT', 'STARRED', 'CATEGORY_PERSONAL',
                           'CATEGORY_SOCIAL', 'CATEGORY_PROMOTIONS', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS'}

            # Remove system labels from consideration
            non_system_labels = set(email_labels) - system_labels

            # If there are non-system, non-automation labels, consider it labeled
            if non_system_labels - automation_label_ids:
                return False

        return True

    def get_unlabeled_emails(self, config: IncrementalScanConfig, max_emails: int = 1000) -> List[Dict]:
        """
        Get emails that don't have automation labels

        Args:
            config: Incremental scan configuration
            max_emails: Maximum number of emails to return

        Returns:
            List of email message objects
        """
        print(f"🔍 Scanning for unlabeled emails...")

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

            while len(unlabeled_emails) < max_emails:
                # Calculate how many to fetch in this batch
                remaining = max_emails - len(unlabeled_emails)
                batch_size = min(config.batch_size, remaining, 500)  # Gmail API limit is 500

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
                    if processed_count % 100 == 0:
                        print(f"   📊 Processed {processed_count} emails, found {len(unlabeled_emails)} unlabeled so far...")

                unlabeled_emails.extend(batch_unlabeled)

                # Get next page token
                next_page_token = result.get('nextPageToken')
                if not next_page_token:
                    break

                # Show progress
                print(f"   📦 Batch complete: +{len(batch_unlabeled)} unlabeled emails (total: {len(unlabeled_emails)})")

        except Exception as e:
            print(f"❌ Error fetching unlabeled emails: {e}")
            return []

        print(f"✅ Found {len(unlabeled_emails)} unlabeled emails out of {processed_count} checked")
        return unlabeled_emails

    def scan_and_label_unlabeled_emails(self, max_emails: int = 1000, days_back: int = 30,
                                      debug: bool = False, only_unlabeled: bool = True,
                                      resume_from_id: str = None) -> Dict[str, int]:
        """
        Scan and label only emails that don't have automation labels

        Args:
            max_emails: Maximum emails to process
            days_back: How many days back to scan (0 = all)
            debug: Show debug information
            only_unlabeled: Only process emails without automation labels
            resume_from_id: Resume processing from specific email ID

        Returns:
            Statistics dictionary
        """
        print("📧 Scanning and labeling unlabeled emails...")
        print(f"📊 Parameters: max_emails={max_emails}, days_back={days_back}, only_unlabeled={only_unlabeled}")
        print("-" * 60)

        # Configure incremental scan
        config = IncrementalScanConfig(
            only_unlabeled=only_unlabeled,
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
        if only_unlabeled:
            emails_to_process = self.get_unlabeled_emails(config, max_emails)
        else:
            # Fallback to original method if not using incremental
            emails_to_process = self._get_all_emails(max_emails, days_back)

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

            print(f"\n🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_emails)} emails)")

            batch_stats = self._process_email_batch(batch_emails, existing_labels, debug)

            # Merge batch stats
            for key in ['processed', 'labeled', 'skipped', 'errors']:
                stats[key] += batch_stats.get(key, 0)

            for category, count in batch_stats.get('categories', {}).items():
                stats['categories'][category] = stats['categories'].get(category, 0) + count

            # Progress update
            progress = ((batch_num + 1) / total_batches) * 100
            print(f"📈 Progress: {progress:.1f}% complete")

            # Rate limiting between batches
            if batch_num < total_batches - 1:
                time.sleep(1)

        # Save processing state
        self.processing_state.update({
            'last_scan_time': datetime.datetime.now().isoformat(),
            'last_processed_id': emails_to_process[-1]['id'] if emails_to_process else None,
            'total_processed': self.processing_state['total_processed'] + stats['processed']
        })

        self._save_processing_state()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 INCREMENTAL EMAIL LABELING SUMMARY")
        print("=" * 60)
        print(f"📧 Total processed: {stats['processed']}")
        print(f"✅ Successfully labeled: {stats['labeled']}")
        print(f"⏭️  Skipped (already labeled/no category): {stats['skipped']}")
        print(f"❌ Errors: {stats['errors']}")

        if stats['categories']:
            print(f"\n📋 Categories applied:")
            for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {category}: {count} emails")

        success_rate = (stats['labeled'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
        print(f"\n📈 Success rate: {success_rate:.1f}%")

        if only_unlabeled:
            print("🎯 Incremental mode: Only processed unlabeled emails")

        print(f"\nIncremental email labeling completed: {stats['labeled']} emails labeled")
        return stats

    def _get_date_string(self, days_back: int) -> str:
        """Get date string for Gmail search query"""
        if days_back <= 0:
            return None
        target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        return target_date.strftime('%Y/%m/%d')

    def _get_all_emails(self, max_emails: int, days_back: int) -> List[Dict]:
        """Fallback method to get all emails (original behavior)"""
        query = None
        if days_back > 0:
            date_str = self._get_date_string(days_back)
            query = f"after:{date_str}"

        try:
            result = self.service.users().messages().list(
                userId='me',
                maxResults=min(max_emails, 500),
                q=query
            ).execute()

            message_ids = [msg['id'] for msg in result.get('messages', [])]

            emails = []
            for msg_id in message_ids:
                email = self.service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                emails.append(email)

            return emails

        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []

    def _process_email_batch(self, batch_emails: List[Dict], existing_labels: Dict, debug: bool) -> Dict:
        """Process a batch of emails"""
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
            with open('processing_state.json', 'r') as f:
                self.processing_state.update(json.load(f))
        except FileNotFoundError:
            pass  # File doesn't exist yet, use defaults
        except Exception as e:
            print(f"⚠️ Could not load processing state: {e}")

    # Import all other methods from the original class
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

    # Add other essential methods (simplified versions)
    def get_existing_labels(self) -> Dict[str, str]:
        """Get existing Gmail labels"""
        try:
            result = self.service.users().labels().list(userId='me').execute()
            labels = result.get('labels', [])
            return {label['name']: label['id'] for label in labels}
        except Exception as e:
            print(f"❌ Error getting labels: {e}")
            return {}

    def calculate_category_score(self, email_data: Dict, category_name: str, category_config: Dict) -> float:
        """Calculate category score (simplified version)"""
        # This is a simplified version - you'd import the full method from the original
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
    """Extended main function with incremental labeling options"""
    parser = argparse.ArgumentParser(description='Gmail Automation Suite - Extended Edition')

    # Basic options
    parser.add_argument('--credentials', default='credentials.json',
                       help='Path to credentials file (default: credentials.json)')
    parser.add_argument('--token', default='token.json',
                       help='Path to token file (default: token.json)')

    # Incremental labeling options
    parser.add_argument('--scan-unlabeled', action='store_true',
                       help='Scan and label only emails without automation labels')
    parser.add_argument('--scan-all-unlabeled', action='store_true',
                       help='Scan ALL unlabeled emails (no date limit)')
    parser.add_argument('--max-emails', type=int, default=1000,
                       help='Maximum emails to process (default: 1000)')
    parser.add_argument('--days-back', type=int, default=30,
                       help='Days back to scan (default: 30, 0 = all)')
    parser.add_argument('--resume-from', type=str,
                       help='Resume processing from specific email ID')
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
    automation = GmailAutomationExtended(args.credentials, args.token, use_ml=not args.disable_ml)

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

    # Handle incremental labeling
    if args.scan_unlabeled or args.scan_all_unlabeled:
        days_back = 0 if args.scan_all_unlabeled else args.days_back
        stats = automation.scan_and_label_unlabeled_emails(
            max_emails=args.max_emails,
            days_back=days_back,
            debug=args.debug_categorization,
            only_unlabeled=True,
            resume_from_id=args.resume_from
        )
        return 0 if stats.get('errors', 0) == 0 else 1

    # Default behavior
    print("🎯 Extended Gmail Automation Suite v4.1")
    print("💡 Use --scan-unlabeled for incremental labeling of new emails")
    print("💡 Use --scan-all-unlabeled for complete unlabeled email scan")
    print("💡 Use --help for all available options")

    return 0

if __name__ == "__main__":
    exit(main())