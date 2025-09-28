#!/usr/bin/env python3
"""
Gmail Automation Suite - Advanced ML-Powered Email Categorization

A comprehensive tool for Gmail management that includes:
- AI-powered email categorization using BERT and topic modeling
- Advanced label creation and management with smart filters
- Hybrid rule-based + machine learning classification
- Smart filter creation with batch processing
- Label consolidation and migration
- Promotional email management
- Inbox organization and cleanup
- Incremental learning capabilities

Author: Gmail Automation Suite
Version: 4.0.0 - ML Enhanced
"""

import os
import re
import time
import json
import argparse
import warnings
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
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

@dataclass
class Label:
    """Data class for Gmail label configuration"""
    name: str
    color: Optional[str] = None
    parent: Optional[str] = None

@dataclass
class Filter:
    """Data class for Gmail filter configuration"""
    label_name: str
    criteria: Dict[str, str]
    action: Optional[Dict[str, any]] = None
    mark_important: bool = False
    auto_archive: bool = True

class GmailAutomation:
    """Main Gmail automation class"""

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

        # Enhanced predefined filters with importance marking
        self.filters = [
            Filter(
                '🏦 Banking & Finance',
                {
                    'query': '(from:(hdfcbank.com OR icicibank.com OR axisbank.com OR sbi.co.in OR kotak.com OR americanexpress.com OR cred.club OR hdfc OR icici OR axis OR indmoney OR nse.co.in OR policybazaar OR zerodha OR groww)) OR (subject:(payment OR bill OR investment OR trading OR insurance OR "credit card"))'
                },
                mark_important=True
            ),
            Filter(
                '📈 Investments & Trading',
                {
                    'query': '(from:(zerodha.com OR groww.in OR upstox.com OR angelone.in OR kfintech.com OR camsonline.com)) OR (subject:("contract note" OR "mutual fund" OR demat OR SIP OR portfolio OR "trade confirmation"))'
                },
                mark_important=True
            ),
            Filter(
                '🔔 Alerts & Security',
                {
                    'query': '(from:(google OR apple) AND subject:(security OR alert OR suspicious)) OR (subject:("security alert" OR "suspicious activity" OR "login attempt"))'
                },
                mark_important=True,
                auto_archive=False
            ),
            Filter(
                '🛒 Shopping & Orders',
                {
                    'query': '(from:(amazon.in OR flipkart.com OR myntra.com OR ajio.com OR nykaa.com OR swiggy.in OR zomato.com OR blinkit.com)) OR (subject:("your order" OR shipped OR delivery OR "order confirmation" OR "out for delivery"))'
                }
            ),
            Filter(
                '📦 Receipts & Archive',
                {
                    'query': '(from:(uber.com OR ola.in OR makemytrip.com OR bookmyshow.com OR netflix.com OR primevideo.com OR hotstar.com OR spotify.com)) OR (subject:(receipt OR invoice OR "booking confirmation" OR bill OR subscription OR "payment successful"))'
                }
            ),
            Filter(
                '🏥 Insurance & Services',
                {
                    'query': '(from:(policybazaar.com OR acko.com OR hdfcergo.com OR digitinsurance.com OR tata1mg OR 1mg OR hospital)) OR (subject:(policy OR premium OR renewal OR claim OR health OR medical))'
                }
            ),
            Filter(
                '📰 Marketing & News',
                {
                    'query': '(from:(googlenews OR marketbrew OR groundnews OR economictimes OR newsletter)) OR (subject:(news OR newsletter OR briefing OR unsubscribe))'
                }
            ),
            Filter(
                '✈️ Travel & Transport',
                {
                    'query': '(from:(makemytrip.com OR goibibo.com OR irctc.co.in OR indigo.com OR airindia.in OR vistara.com OR uber.com OR ola.in)) OR (subject:(ticket OR "booking confirmation" OR PNR OR "travel itinerary" OR "flight status"))'
                }
            )
        ]

    def validate_environment(self) -> bool:
        """Validate the environment and required files"""
        print("🔍 Validating environment...")

        if not os.path.exists(self.credentials_file):
            print(f"❌ Error: {self.credentials_file} not found!")
            print("Please download OAuth 2.0 credentials from Google Cloud Console")
            return False

        try:
            with open(self.credentials_file, 'r') as f:
                creds_data = json.load(f)
                if 'installed' not in creds_data and 'web' not in creds_data:
                    print("❌ Error: Invalid credentials file format!")
                    return False
        except json.JSONDecodeError:
            print("❌ Error: Credentials file is not valid JSON!")
            return False

        print("✅ Environment validation passed")
        return True

    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        print("🔐 Authenticating with Gmail API...")

        creds = None
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                print(f"⚠️  Warning: Could not load existing token: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    print(f"⚠️  Could not refresh credentials: {e}")
                    creds = None

            if not creds:
                try:
                    print("🌐 Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"❌ OAuth flow failed: {e}")
                    return False

            # Save credentials
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                print(f"💾 Credentials saved to {self.token_file}")
            except Exception as e:
                print(f"⚠️  Warning: Could not save token: {e}")

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            # Test the connection
            self.service.users().getProfile(userId='me').execute()
            print("✅ Authentication successful!")
            return True
        except Exception as e:
            print(f"❌ Failed to build Gmail service: {e}")
            return False

    def get_existing_labels(self) -> Dict[str, str]:
        """Get existing labels and cache them"""
        if self.labels_cache:
            return self.labels_cache

        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            for label in labels:
                self.labels_cache[label['name']] = label['id']

            print(f"📋 Found {len(self.labels_cache)} existing labels")
            return self.labels_cache

        except HttpError as e:
            print(f"❌ Error fetching labels: {e}")
            return {}

    def create_labels(self) -> Tuple[int, int, int]:
        """Create predefined labels"""
        print("\n📝 Creating Gmail labels...")
        print("-" * 50)

        existing_labels = self.get_existing_labels()
        created_count = 0
        exists_count = 0
        failed_count = 0

        for label in self.labels:
            print(f"Processing: {label.name}")

            if label.name in existing_labels:
                print(f"  ✓ Already exists")
                exists_count += 1
                continue

            try:
                label_body = {
                    'name': label.name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }

                if label.color:
                    label_body['color'] = {
                        'backgroundColor': label.color,
                        'textColor': '#ffffff'
                    }

                result = self.service.users().labels().create(userId='me', body=label_body).execute()
                print(f"  ✅ Created successfully (ID: {result.get('id')})")

                # Update cache
                self.labels_cache[label.name] = result.get('id')
                created_count += 1

            except HttpError as error:
                if error.resp.status == 409:
                    print(f"  ✓ Already exists (API conflict)")
                    exists_count += 1
                elif error.resp.status == 400 and "color" in str(error):
                    # Try creating label without color if color is invalid
                    print(f"  ⚠️  Invalid color, creating without color...")
                    try:
                        label_body_no_color = {
                            'name': label.name,
                            'labelListVisibility': 'labelShow',
                            'messageListVisibility': 'show'
                        }
                        result = self.service.users().labels().create(userId='me', body=label_body_no_color).execute()
                        print(f"  ✅ Created successfully without color (ID: {result.get('id')})")
                        self.labels_cache[label.name] = result.get('id')
                        created_count += 1
                    except Exception as fallback_error:
                        print(f"  ❌ Fallback failed: {fallback_error}")
                        failed_count += 1
                else:
                    print(f"  ❌ HTTP Error: {error}")
                    failed_count += 1
            except Exception as e:
                print(f"  ❌ Error: {e}")
                failed_count += 1

        return created_count, exists_count, failed_count

    def create_filters(self) -> Tuple[int, int]:
        """Create predefined filters"""
        print("\n🔍 Creating Gmail filters...")
        print("-" * 50)

        # Refresh labels cache
        existing_labels = self.get_existing_labels()
        created_count = 0
        failed_count = 0

        for filter_config in self.filters:
            print(f"Processing filter for: {filter_config.label_name}")

            # Check if label exists
            if filter_config.label_name not in existing_labels:
                print(f"  ⚠️  Label '{filter_config.label_name}' not found, skipping")
                failed_count += 1
                continue

            try:
                # Prepare enhanced filter body with importance marking
                action_labels = [existing_labels[filter_config.label_name]]

                # Add importance marking if specified
                if filter_config.mark_important:
                    action_labels.append('IMPORTANT')

                filter_body = {
                    'criteria': filter_config.criteria,
                    'action': {
                        'addLabelIds': action_labels
                    }
                }

                # Auto-archive unless explicitly disabled
                if filter_config.auto_archive:
                    filter_body['action']['removeLabelIds'] = ['INBOX']

                # Merge custom actions if provided
                if filter_config.action:
                    filter_body['action'].update(filter_config.action)

                result = self.service.users().settings().filters().create(
                    userId='me',
                    body=filter_body
                ).execute()

                importance_note = " (marked important)" if filter_config.mark_important else ""
                archive_note = " (auto-archive)" if filter_config.auto_archive else ""
                print(f"  ✅ Filter created successfully{importance_note}{archive_note}")
                created_count += 1

            except HttpError as error:
                print(f"  ❌ HTTP Error: {error}")
                failed_count += 1
            except Exception as e:
                print(f"  ❌ Error: {e}")
                failed_count += 1

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        return created_count, failed_count

    def scan_promotional_emails(self, max_results: int = 100) -> List[Dict]:
        """Scan for promotional emails in inbox"""
        print(f"\n📧 Scanning for promotional emails (max {max_results})...")

        query = 'in:inbox unsubscribe -category:{social,promotions}'

        try:
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = response.get('messages', [])
            print(f"📊 Found {len(messages)} potential promotional emails")
            return messages

        except HttpError as error:
            print(f"❌ Error scanning emails: {error}")
            return []

    def migrate_emails_to_label(self, from_labels: List[str], to_label: str, max_messages: int = 1000) -> int:
        """Migrate emails from old labels to new label with batch processing"""
        print(f"\n🔄 Migrating emails from {from_labels} to {to_label}...")

        # Build query to find emails with any of the source labels
        query = " OR ".join([f"label:{label_id}" for label_id in from_labels])

        try:
            # Get all message IDs with pagination
            all_message_ids = []
            request = self.service.users().messages().list(userId='me', q=query, maxResults=500)

            while request is not None and len(all_message_ids) < max_messages:
                response = request.execute()
                messages = response.get('messages', [])
                if messages:
                    all_message_ids.extend([msg['id'] for msg in messages])
                request = self.service.users().messages().list_next(request, response)

            if not all_message_ids:
                print("  📭 No messages found to migrate")
                return 0

            print(f"  📧 Found {len(all_message_ids)} messages to migrate")

            # Get label ID for destination
            existing_labels = self.get_existing_labels()
            if to_label not in existing_labels:
                print(f"  ❌ Destination label '{to_label}' not found")
                return 0

            to_label_id = existing_labels[to_label]

            # Process in batches of 100
            migrated_count = 0
            for i in range(0, len(all_message_ids), 100):
                batch_ids = all_message_ids[i:i + 100]
                batch_body = {
                    'ids': batch_ids,
                    'addLabelIds': [to_label_id],
                    'removeLabelIds': from_labels
                }

                try:
                    self.service.users().messages().batchModify(userId='me', body=batch_body).execute()
                    batch_num = i // 100 + 1
                    total_batches = (len(all_message_ids) + 99) // 100
                    print(f"    ✅ Processed batch {batch_num}/{total_batches}")
                    migrated_count += len(batch_ids)
                    time.sleep(1)  # Rate limiting
                except HttpError as e:
                    print(f"    ❌ Batch {batch_num} failed: {e}")

            print(f"  🎉 Migration complete: {migrated_count} messages moved")
            return migrated_count

        except HttpError as error:
            print(f"  ❌ Migration failed: {error}")
            return 0

    def delete_labels(self, label_names: List[str]) -> Tuple[int, int]:
        """Delete specified labels"""
        print(f"\n🗑️  Deleting {len(label_names)} labels...")

        existing_labels = self.get_existing_labels()
        deleted_count = 0
        failed_count = 0

        for label_name in label_names:
            if label_name not in existing_labels:
                print(f"  ⚠️  Label '{label_name}' not found, skipping")
                failed_count += 1
                continue

            try:
                label_id = existing_labels[label_name]
                self.service.users().labels().delete(userId='me', id=label_id).execute()
                print(f"  ✅ Deleted: {label_name}")
                deleted_count += 1

                # Remove from cache
                if label_name in self.labels_cache:
                    del self.labels_cache[label_name]

            except HttpError as error:
                print(f"  ❌ Failed to delete '{label_name}': {error}")
                failed_count += 1

        return deleted_count, failed_count

    def clear_existing_filters(self) -> int:
        """Delete all existing filters to start fresh"""
        print("\n🧹 Clearing existing filters...")

        try:
            existing_filters = self.service.users().settings().filters().list(userId='me').execute().get('filter', [])

            if not existing_filters:
                print("  📭 No existing filters found")
                return 0

            print(f"  🔍 Found {len(existing_filters)} existing filters")

            deleted_count = 0
            for filter_obj in existing_filters:
                try:
                    self.service.users().settings().filters().delete(userId='me', id=filter_obj['id']).execute()
                    deleted_count += 1
                except HttpError as e:
                    print(f"    ⚠️  Could not delete filter {filter_obj['id']}: {e}")

            print(f"  ✅ Deleted {deleted_count} existing filters")
            return deleted_count

        except HttpError as error:
            print(f"  ❌ Error clearing filters: {error}")
            return 0

    def cleanup_automation_labels_and_filters(self, force: bool = False) -> Tuple[int, int]:
        """
        Remove all labels and filters created by this automation suite.

        Args:
            force: Skip confirmation prompts if True

        Returns:
            Tuple of (labels_deleted, filters_deleted)
        """
        print("\n🧹 Gmail Automation Cleanup")
        print("=" * 50)
        print("⚠️  This will remove ALL labels and filters created by this automation.")
        print("📧 Emails will NOT be deleted - only labels will be removed.")

        if not force:
            print("\n🏷️  Labels that will be deleted:")
            for label in self.labels:
                print(f"   • {label.name}")

            print("\n🔍 All existing filters will also be cleared.")

            confirm = input("\n❓ Are you sure you want to proceed? (type 'yes' to confirm): ")
            if confirm.lower() != 'yes':
                print("❌ Cleanup cancelled.")
                return 0, 0

        print("\n🚀 Starting cleanup process...")

        # Get existing labels before cleanup
        existing_labels = self.get_existing_labels()
        automation_label_names = [label.name for label in self.labels]

        # Step 1: Remove all filters first
        print("\n🔍 Clearing all filters...")
        filters_deleted = self.clear_existing_filters()

        # Step 2: Remove email labels from messages (optional - just remove the labels)
        print("\n📧 Removing labels from emails...")
        emails_processed = 0
        for label_name in automation_label_names:
            if label_name in existing_labels:
                label_id = existing_labels[label_name]

                # Find emails with this label
                try:
                    query = f'label:{label_id}'
                    response = self.service.users().messages().list(
                        userId='me', q=query, maxResults=500
                    ).execute()

                    messages = response.get('messages', [])
                    if messages:
                        print(f"   📩 Found {len(messages)} emails with label '{label_name}'")

                        # Remove label from emails in batches
                        for i in range(0, len(messages), 100):
                            batch = messages[i:i + 100]
                            batch_ids = [msg['id'] for msg in batch]

                            self.service.users().messages().batchModify(
                                userId='me',
                                body={'ids': batch_ids, 'removeLabelIds': [label_id]}
                            ).execute()

                            emails_processed += len(batch_ids)
                            time.sleep(0.5)  # Rate limiting

                except Exception as e:
                    print(f"   ⚠️  Could not process emails for {label_name}: {e}")

        print(f"   ✅ Processed {emails_processed} emails")

        # Step 3: Delete the labels themselves
        print("\n🗑️  Deleting automation labels...")
        labels_deleted, labels_failed = self.delete_labels(automation_label_names)

        # Final summary
        print("\n" + "=" * 50)
        print("🎯 CLEANUP SUMMARY")
        print("=" * 50)
        print(f"🗑️  Labels deleted: {labels_deleted}")
        print(f"🔍 Filters deleted: {filters_deleted}")
        print(f"📧 Emails processed: {emails_processed}")
        print(f"❌ Failed operations: {labels_failed}")

        if labels_failed == 0:
            print("\n✅ Gmail automation cleanup completed successfully!")
            print("📧 Your emails are safe - only organization labels were removed.")
        else:
            print(f"\n⚠️  Cleanup completed with {labels_failed} errors")

        return labels_deleted, filters_deleted

    def reset_gmail_to_default(self, force: bool = False) -> bool:
        """
        Complete reset: Remove all automation labels, filters, and return Gmail to default state.
        """
        print("\n🔄 Gmail Complete Reset")
        print("=" * 50)
        print("⚠️  This will completely undo ALL Gmail automation changes:")
        print("   • Remove all automation labels")
        print("   • Clear all filters")
        print("   • Remove labels from existing emails")
        print("   • Reset Gmail to pre-automation state")

        if not force:
            confirm = input("\n❓ Type 'RESET' to confirm complete reset: ")
            if confirm != 'RESET':
                print("❌ Reset cancelled.")
                return False

        print("\n🚀 Performing complete Gmail reset...")

        # Perform cleanup
        labels_deleted, filters_deleted = self.cleanup_automation_labels_and_filters(force=True)

        print("\n🎉 Gmail has been reset to pre-automation state!")
        print("✅ You can now re-run the automation with fresh settings if desired.")

        return True

    def diagnose_label_visibility(self) -> Dict:
        """
        Diagnose why labels might not be visible in Gmail web interface.
        Returns detailed information about label status and visibility.
        """
        print("\n🔍 Diagnosing Label Visibility Issues")
        print("=" * 50)

        diagnosis = {
            'total_labels': 0,
            'automation_labels': {},
            'visibility_issues': [],
            'recommendations': []
        }

        try:
            # Get all labels
            results = self.service.users().labels().list(userId='me').execute()
            all_labels = results.get('labels', [])
            diagnosis['total_labels'] = len(all_labels)

            print(f"📋 Found {len(all_labels)} total labels in your Gmail account")

            # Check automation labels specifically
            automation_label_names = [label.name for label in self.labels]

            print(f"\n🔍 Checking {len(automation_label_names)} automation labels:")

            for label_name in automation_label_names:
                # Find the label in the API response
                found_label = None
                for label in all_labels:
                    if label['name'] == label_name:
                        found_label = label
                        break

                if found_label:
                    label_info = {
                        'id': found_label['id'],
                        'name': found_label['name'],
                        'type': found_label.get('type', 'user'),
                        'labelListVisibility': found_label.get('labelListVisibility', 'unknown'),
                        'messageListVisibility': found_label.get('messageListVisibility', 'unknown'),
                        'messagesTotal': found_label.get('messagesTotal', 0),
                        'messagesUnread': found_label.get('messagesUnread', 0),
                        'threadsTotal': found_label.get('threadsTotal', 0),
                        'threadsUnread': found_label.get('threadsUnread', 0),
                        'color': found_label.get('color', {})
                    }

                    diagnosis['automation_labels'][label_name] = label_info

                    # Check visibility settings
                    list_vis = label_info['labelListVisibility']
                    msg_vis = label_info['messageListVisibility']

                    print(f"   ✅ {label_name}")
                    print(f"      ID: {label_info['id']}")
                    print(f"      List Visibility: {list_vis}")
                    print(f"      Message Visibility: {msg_vis}")
                    print(f"      Total Messages: {label_info['messagesTotal']}")
                    print(f"      Color: {label_info['color']}")

                    # Check for visibility issues
                    if list_vis == 'labelHide':
                        diagnosis['visibility_issues'].append(f"{label_name}: Hidden in label list")
                    if msg_vis == 'hide':
                        diagnosis['visibility_issues'].append(f"{label_name}: Hidden in message list")
                    if label_info['messagesTotal'] == 0:
                        diagnosis['visibility_issues'].append(f"{label_name}: No messages labeled")

                else:
                    print(f"   ❌ {label_name} - NOT FOUND")
                    diagnosis['visibility_issues'].append(f"{label_name}: Label not found in Gmail")

            # Generate recommendations
            if diagnosis['visibility_issues']:
                print(f"\n⚠️  Found {len(diagnosis['visibility_issues'])} potential issues:")
                for issue in diagnosis['visibility_issues']:
                    print(f"   • {issue}")

                # Generate recommendations
                if any('Hidden in label list' in issue for issue in diagnosis['visibility_issues']):
                    diagnosis['recommendations'].append("Fix label list visibility with --fix-visibility")

                if any('No messages labeled' in issue for issue in diagnosis['visibility_issues']):
                    diagnosis['recommendations'].append("Run email scanning to apply labels: --scan-emails")

                if any('Label not found' in issue for issue in diagnosis['visibility_issues']):
                    diagnosis['recommendations'].append("Create missing labels: --labels-only")

            else:
                print("\n✅ All automation labels appear to be configured correctly!")

            # Gmail web interface tips
            print(f"\n💡 Gmail Web Interface Tips:")
            print(f"   • Labels appear in the left sidebar under 'Labels'")
            print(f"   • You may need to scroll down or click 'More' to see all labels")
            print(f"   • Labels only appear if they have messages assigned")
            print(f"   • Try refreshing your Gmail page (Ctrl+F5 or Cmd+R)")
            print(f"   • Check if labels are collapsed - look for a small arrow next to 'Labels'")

            return diagnosis

        except HttpError as error:
            print(f"❌ Error during diagnosis: {error}")
            diagnosis['error'] = str(error)
            return diagnosis

    def fix_label_visibility(self) -> Tuple[int, int]:
        """
        Fix label visibility issues by ensuring all automation labels are visible.
        """
        print("\n🔧 Fixing Label Visibility Issues")
        print("=" * 50)

        fixed_count = 0
        failed_count = 0

        # Get existing labels
        existing_labels = self.get_existing_labels()
        automation_label_names = [label.name for label in self.labels]

        for label_name in automation_label_names:
            if label_name in existing_labels:
                label_id = existing_labels[label_name]

                try:
                    # Get current label details
                    current_label = self.service.users().labels().get(userId='me', id=label_id).execute()

                    # Check if visibility needs fixing
                    needs_fix = False
                    update_body = {}

                    if current_label.get('labelListVisibility') != 'labelShow':
                        update_body['labelListVisibility'] = 'labelShow'
                        needs_fix = True

                    if current_label.get('messageListVisibility') != 'show':
                        update_body['messageListVisibility'] = 'show'
                        needs_fix = True

                    if needs_fix:
                        # Update label visibility
                        self.service.users().labels().patch(
                            userId='me',
                            id=label_id,
                            body=update_body
                        ).execute()

                        print(f"   ✅ Fixed visibility for: {label_name}")
                        fixed_count += 1
                    else:
                        print(f"   ✓ Already visible: {label_name}")

                except HttpError as error:
                    print(f"   ❌ Failed to fix {label_name}: {error}")
                    failed_count += 1

        print(f"\n📊 Visibility Fix Summary:")
        print(f"   ✅ Fixed: {fixed_count}")
        print(f"   ❌ Failed: {failed_count}")

        return fixed_count, failed_count

    def load_categories_config(self) -> Dict:
        """Load email categorization configuration from JSON file"""
        config_file = os.path.join(os.path.dirname(__file__), 'email_categories.json')
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  Categories config file not found, using fallback rules")
            return self.get_fallback_config()
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid categories config: {e}, using fallback rules")
            return self.get_fallback_config()

    def get_fallback_config(self) -> Dict:
        """Fallback configuration if JSON file is not available"""
        return {
            "categories": {
                "🏦 Banking & Finance": {
                    "priority": 8,
                    "domains": {"high_confidence": ["hdfcbank.com", "icicibank.com", "paytm.com"]},
                    "keywords": {"subject_medium": ["payment", "transaction", "bank", "otp"]}
                }
            },
            "global_settings": {"confidence_threshold": 0.6},
            "scoring_weights": {"domain_high_confidence": 1.0, "subject_medium": 0.4}
        }

    def calculate_category_score(self, email_data: Dict, category_name: str, category_config: Dict) -> float:
        """Calculate confidence score for a specific category"""
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()
        snippet = email_data.get('snippet', '').lower()

        score = 0.0
        weights = self.categories_config.get('scoring_weights', {})

        # Domain scoring
        domains = category_config.get('domains', {})
        for confidence_level, domain_list in domains.items():
            weight_key = f"domain_{confidence_level}"
            weight = weights.get(weight_key, 0.5)

            for domain in domain_list:
                if domain.lower() in sender:
                    score += weight
                    break  # Only count once per confidence level

        # Subject keyword scoring
        keywords = category_config.get('keywords', {})
        for keyword_type, keyword_list in keywords.items():
            if keyword_type.startswith('subject_'):
                weight = weights.get(keyword_type, 0.3)
                for keyword in keyword_list:
                    if keyword.lower() in subject:
                        score += weight

        # Content keyword scoring (if enabled)
        if self.categories_config.get('global_settings', {}).get('enable_content_analysis', True):
            for keyword_type, keyword_list in keywords.items():
                if keyword_type.startswith('content_'):
                    weight = weights.get(keyword_type, 0.2)
                    for keyword in keyword_list:
                        if keyword.lower() in snippet:
                            score += weight

        # Exclusion penalties
        exclusions = category_config.get('exclusions', [])
        exclusion_penalty = weights.get('exclusion_penalty', -0.5)
        for exclusion in exclusions:
            if exclusion.lower() in subject + ' ' + snippet:
                score += exclusion_penalty

        # Priority bonus (higher priority categories get slight boost)
        priority = category_config.get('priority', 1)
        priority_bonus = weights.get('priority_bonus', 0.1)
        score += (priority / 10) * priority_bonus

        return max(0.0, score)  # Ensure non-negative score

    def categorize_email(self, email_data: Dict) -> Optional[str]:
        """
        Advanced email categorization using hybrid ML + rule-based approach.
        Returns the highest confidence category or None if below threshold.
        """
        # Use ML categorizer if available
        if self.use_ml and self.ml_categorizer:
            # Get rule-based prediction first
            rule_based_category = self._categorize_email_rule_based(email_data)
            rule_based_confidence = self._get_rule_based_confidence(email_data, rule_based_category)

            # Get hybrid prediction
            result = self.ml_categorizer.hybrid_categorize(
                email_data,
                rule_based_result=(rule_based_category, rule_based_confidence) if rule_based_category else None
            )

            return result.get('final_category')
        else:
            # Fallback to rule-based categorization
            return self._categorize_email_rule_based(email_data)

    def _categorize_email_rule_based(self, email_data: Dict) -> Optional[str]:
        """
        Original rule-based email categorization method.
        """
        categories = self.categories_config.get('categories', {})
        global_settings = self.categories_config.get('global_settings', {})
        confidence_threshold = global_settings.get('confidence_threshold', 0.4)

        # Calculate scores for all categories
        category_scores = {}
        for category_name, category_config in categories.items():
            score = self.calculate_category_score(email_data, category_name, category_config)
            if score > 0:
                category_scores[category_name] = score

        # Return highest scoring category if above threshold
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]

            if best_score >= confidence_threshold:
                return best_category

        return None

    def _get_rule_based_confidence(self, email_data: Dict, category: str) -> float:
        """
        Get confidence score for rule-based categorization.
        """
        if not category:
            return 0.0

        categories = self.categories_config.get('categories', {})
        if category in categories:
            return self.calculate_category_score(email_data, category, categories[category])
        return 0.0

    def categorize_email_debug(self, email_data: Dict) -> Dict:
        """
        Debug version that returns detailed scoring information including ML predictions.
        Useful for understanding why emails are categorized a certain way.
        """
        # Get rule-based scores
        categories = self.categories_config.get('categories', {})
        global_settings = self.categories_config.get('global_settings', {})
        confidence_threshold = global_settings.get('confidence_threshold', 0.4)

        category_scores = {}
        for category_name, category_config in categories.items():
            score = self.calculate_category_score(email_data, category_name, category_config)
            category_scores[category_name] = round(score, 3)

        # Determine rule-based best category
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

        # Add ML predictions if available
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

    def process_email_batch_concurrent(self, email_batch: List[str], existing_labels: Dict[str, str]) -> Dict[str, int]:
        """
        Process a batch of emails concurrently using ThreadPoolExecutor

        Args:
            email_batch: List of email IDs to process
            existing_labels: Dictionary mapping label names to IDs

        Returns:
            Dictionary with processing statistics
        """
        batch_stats = {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0, 'categories': {}}

        def process_single_email(msg_id: str) -> Dict:
            """Process a single email and return results"""
            try:
                # Get email details
                email = self.service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()

                # Extract email data
                headers = {}
                if 'payload' in email and 'headers' in email['payload']:
                    headers = {h['name'].lower(): h['value'] for h in email['payload']['headers']}

                email_data = {
                    'sender': headers.get('from', ''),
                    'subject': headers.get('subject', ''),
                    'snippet': email.get('snippet', '')
                }

                # Categorize email
                suggested_label = self.categorize_email(email_data)

                result = {
                    'email_id': msg_id,
                    'processed': True,
                    'suggested_label': suggested_label,
                    'current_labels': email.get('labelIds', []),
                    'email_data': email_data
                }

                return result

            except Exception as e:
                return {
                    'email_id': msg_id,
                    'processed': False,
                    'error': str(e)
                }

        # Process emails concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all email processing tasks
            future_to_email = {executor.submit(process_single_email, msg_id): msg_id
                             for msg_id in email_batch}

            # Collect results as they complete
            for future in as_completed(future_to_email):
                result = future.result()

                if result['processed']:
                    batch_stats['processed'] += 1

                    suggested_label = result['suggested_label']
                    current_labels = result['current_labels']

                    if suggested_label and suggested_label in existing_labels:
                        target_label_id = existing_labels[suggested_label]

                        if target_label_id not in current_labels:
                            # Apply the label
                            try:
                                self.service.users().messages().modify(
                                    userId='me',
                                    id=result['email_id'],
                                    body={'addLabelIds': [target_label_id]}
                                ).execute()

                                batch_stats['labeled'] += 1
                                batch_stats['categories'][suggested_label] = batch_stats['categories'].get(suggested_label, 0) + 1

                            except Exception as e:
                                batch_stats['errors'] += 1
                        else:
                            batch_stats['skipped'] += 1
                    else:
                        batch_stats['skipped'] += 1
                else:
                    batch_stats['errors'] += 1

        return batch_stats

    def scan_and_label_emails_concurrent(self, max_emails: int = 1000, days_back: int = 30,
                                        debug: bool = False, max_workers: int = 3) -> Dict[str, int]:
        """
        Concurrent version of scan_and_label_emails with improved performance

        Args:
            max_emails: Maximum number of emails to process
            days_back: How many days back to scan (0 = all emails)
            debug: Show debug information
            max_workers: Number of concurrent processing threads

        Returns:
            Dictionary with labeling statistics
        """
        print(f"\n🚀 Concurrent email scanning and labeling...")
        print(f"📊 Parameters: max_emails={max_emails}, days_back={days_back}, workers={max_workers}")
        print("-" * 60)

        # Build query for recent emails
        query_parts = ['in:inbox OR in:sent']
        if days_back > 0:
            query_parts.append(f'newer_than:{days_back}d')

        query = ' '.join(query_parts)

        try:
            # Get existing labels for mapping
            existing_labels = self.get_existing_labels()

            # Get list of emails to process
            print("🔍 Fetching email list...")
            all_message_ids = []
            request = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(max_emails, 500)
            )

            while request and len(all_message_ids) < max_emails:
                result = request.execute()
                messages = result.get('messages', [])

                for message in messages:
                    all_message_ids.append(message['id'])
                    if len(all_message_ids) >= max_emails:
                        break

                request = self.service.users().messages().list_next(request, result)

            print(f"  📩 Found {len(all_message_ids)} emails to process")

            if not all_message_ids:
                print("No emails found to process.")
                return {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0}

            # Process emails in concurrent batches
            batch_size = 20  # Smaller batches for concurrent processing
            total_stats = {'processed': 0, 'labeled': 0, 'skipped': 0, 'errors': 0, 'categories': {}}

            total_batches = (len(all_message_ids) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(all_message_ids))
                batch_ids = all_message_ids[start_idx:end_idx]

                print(f"\n🔄 Processing concurrent batch {batch_num + 1}/{total_batches} ({len(batch_ids)} emails)")

                # Process batch concurrently
                batch_stats = self.process_email_batch_concurrent(batch_ids, existing_labels)

                # Merge batch stats
                for key in ['processed', 'labeled', 'skipped', 'errors']:
                    total_stats[key] += batch_stats.get(key, 0)

                for category, count in batch_stats.get('categories', {}).items():
                    total_stats['categories'][category] = total_stats['categories'].get(category, 0) + count

                # Progress update
                progress = ((batch_num + 1) / total_batches) * 100
                print(f"📈 Progress: {progress:.1f}% | Batch stats: {batch_stats['processed']} processed, {batch_stats['labeled']} labeled")

                # Rate limiting between batches
                if batch_num < total_batches - 1:
                    time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error during concurrent processing: {e}")
            return {'error': str(e)}

        # Print summary
        print("\n" + "=" * 60)
        print("📊 CONCURRENT EMAIL LABELING SUMMARY")
        print("=" * 60)
        print(f"📧 Total processed: {total_stats['processed']}")
        print(f"✅ Successfully labeled: {total_stats['labeled']}")
        print(f"⏭️  Skipped (already labeled/no category): {total_stats['skipped']}")
        print(f"❌ Errors: {total_stats['errors']}")

        if total_stats['categories']:
            print(f"\n📋 Categories applied:")
            for category, count in sorted(total_stats['categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {category}: {count} emails")

        success_rate = (total_stats['labeled'] / total_stats['processed'] * 100) if total_stats['processed'] > 0 else 0
        print(f"\n📈 Success rate: {success_rate:.1f}%")
        print("🚀 Concurrent processing: Improved performance with parallel execution")

        print(f"\nConcurrent email labeling completed: {total_stats['labeled']} emails labeled")
        return total_stats

    def scan_and_label_emails(self, max_emails: int = 1000, days_back: int = 30, debug: bool = False) -> Dict[str, int]:
        """
        Scan existing emails and apply appropriate labels based on content analysis.

        Args:
            max_emails: Maximum number of emails to process
            days_back: How many days back to scan (0 = all emails)

        Returns:
            Dictionary with labeling statistics
        """
        print(f"\n📧 Scanning and labeling emails...")
        print(f"📊 Parameters: max_emails={max_emails}, days_back={days_back}")
        print("-" * 60)

        # Build query for recent emails
        query_parts = ['in:inbox OR in:sent']
        if days_back > 0:
            query_parts.append(f'newer_than:{days_back}d')

        query = ' '.join(query_parts)

        try:
            # Get existing labels for mapping
            existing_labels = self.get_existing_labels()

            # Get list of emails to process
            print("🔍 Fetching email list...")
            all_message_ids = []
            request = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(500, max_emails)
            )

            while request is not None and len(all_message_ids) < max_emails:
                response = request.execute()
                messages = response.get('messages', [])
                if messages:
                    all_message_ids.extend([msg['id'] for msg in messages[:max_emails - len(all_message_ids)]])
                    print(f"  📩 Found {len(all_message_ids)} emails so far...")
                request = self.service.users().messages().list_next(request, response)

                if len(all_message_ids) >= max_emails:
                    break

            if not all_message_ids:
                print("📭 No emails found to process")
                return {}

            print(f"📬 Processing {len(all_message_ids)} emails...")

            # Statistics tracking
            stats = {
                'processed': 0,
                'labeled': 0,
                'skipped': 0,
                'errors': 0,
                'categories': {}
            }

            # Process emails in batches
            batch_size = 50
            for i in range(0, len(all_message_ids), batch_size):
                batch_ids = all_message_ids[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(all_message_ids) + batch_size - 1) // batch_size

                print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch_ids)} emails)")

                for msg_id in batch_ids:
                    try:
                        # Get email details
                        email = self.service.users().messages().get(
                            userId='me',
                            id=msg_id,
                            format='metadata',
                            metadataHeaders=['From', 'To', 'Subject']
                        ).execute()

                        # Extract email data
                        headers = {h['name'].lower(): h['value'] for h in email.get('payload', {}).get('headers', [])}
                        email_data = {
                            'sender': headers.get('from', ''),
                            'subject': headers.get('subject', ''),
                            'snippet': email.get('snippet', '')
                        }

                        # Categorize email (with debug info if requested)
                        if debug:
                            debug_info = self.categorize_email_debug(email_data)
                            suggested_label = debug_info['final_category']

                            # Show debug info for first few emails in batch
                            if len([x for x in batch_ids if batch_ids.index(x) <= batch_ids.index(msg_id)]) <= 2:
                                print(f"    🔍 DEBUG: {debug_info['email']['sender'][:30]}")
                                print(f"       Subject: {debug_info['email']['subject']}")
                                print(f"       Rule-based scores: {debug_info['rule_based']['scores']}")
                                if 'ml_prediction' in debug_info:
                                    print(f"       ML method: {debug_info.get('method_used', 'unknown')}")
                                    print(f"       ML confidence: {debug_info.get('final_confidence', 0):.2f}")
                                print(f"       Final result: {suggested_label}")
                        else:
                            suggested_label = self.categorize_email(email_data)

                        stats['processed'] += 1

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

                                stats['labeled'] += 1
                                stats['categories'][suggested_label] = stats['categories'].get(suggested_label, 0) + 1

                                # Show progress for first few in batch
                                if len([x for x in batch_ids if batch_ids.index(x) <= batch_ids.index(msg_id)]) <= 3:
                                    sender_short = email_data['sender'].split('@')[0] if '@' in email_data['sender'] else email_data['sender'][:30]
                                    subject_short = email_data['subject'][:40] + "..." if len(email_data['subject']) > 40 else email_data['subject']
                                    print(f"    ✅ {sender_short[:20]}: {subject_short} → {suggested_label}")
                            else:
                                stats['skipped'] += 1
                        else:
                            stats['skipped'] += 1

                        # Rate limiting
                        if stats['processed'] % 20 == 0:
                            time.sleep(1)

                    except HttpError as e:
                        if e.resp.status == 429:  # Rate limit
                            print(f"    ⏳ Rate limit hit, waiting 5 seconds...")
                            time.sleep(5)
                        else:
                            stats['errors'] += 1
                            if stats['errors'] <= 3:  # Only show first few errors
                                print(f"    ❌ Error processing email: {e}")
                    except Exception as e:
                        stats['errors'] += 1
                        if stats['errors'] <= 3:
                            print(f"    ❌ Unexpected error: {e}")

                # Progress update
                progress = ((i + batch_size) / len(all_message_ids)) * 100
                print(f"📈 Progress: {min(100, progress):.1f}% complete")

                # Batch delay
                time.sleep(2)

            # Final statistics
            print("\n" + "=" * 60)
            print("📊 EMAIL LABELING SUMMARY")
            print("=" * 60)
            print(f"📧 Total processed: {stats['processed']}")
            print(f"✅ Successfully labeled: {stats['labeled']}")
            print(f"⏭️  Skipped (already labeled/no category): {stats['skipped']}")
            print(f"❌ Errors: {stats['errors']}")

            if stats['categories']:
                print(f"\n🏷️  Labels applied:")
                for label, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                    print(f"   {label}: {count} emails")

            return stats

        except Exception as e:
            print(f"❌ Email scanning failed: {e}")
            return {'error': str(e)}

    def generate_report(self) -> str:
        """Generate a summary report"""
        report = []
        report.append("=" * 60)
        report.append("📋 GMAIL AUTOMATION REPORT")
        report.append("=" * 60)
        report.append(f"🗓️  Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📁 Working Directory: {os.getcwd()}")
        report.append(f"🔑 Token File: {self.token_file}")
        report.append(f"📊 Labels in Cache: {len(self.labels_cache)}")

        return "\n".join(report)

    def run_full_automation(self) -> bool:
        """Run the complete automation suite"""
        print("🚀 Starting Gmail Automation Suite")
        print("=" * 60)

        # Validate environment
        if not self.validate_environment():
            return False

        # Authenticate
        if not self.authenticate():
            return False

        # Create labels
        created, exists, failed = self.create_labels()

        print(f"\n📊 Label Creation Summary:")
        print(f"  ✅ Created: {created}")
        print(f"  ℹ️  Already existed: {exists}")
        print(f"  ❌ Failed: {failed}")

        # Create filters
        if created > 0 or exists > 0:  # Only create filters if we have labels
            filter_created, filter_failed = self.create_filters()

            print(f"\n📊 Filter Creation Summary:")
            print(f"  ✅ Created: {filter_created}")
            print(f"  ❌ Failed: {filter_failed}")

        # Generate final report
        print(self.generate_report())

        success = (failed == 0)
        if success:
            print("\n🎉 Gmail automation completed successfully!")
        else:
            print(f"\n⚠️  Automation completed with {failed} errors")

        return success


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Gmail Automation Suite')
    parser.add_argument('--credentials', default='credentials.json',
                       help='Path to credentials file (default: credentials.json)')
    parser.add_argument('--token', default='token.json',
                       help='Path to token file (default: token.json)')
    parser.add_argument('--labels-only', action='store_true',
                       help='Only create labels, skip filters')
    parser.add_argument('--filters-only', action='store_true',
                       help='Only create filters, skip labels')
    parser.add_argument('--scan-promos', action='store_true',
                       help='Scan for promotional emails')
    parser.add_argument('--clear-filters', action='store_true',
                       help='Clear all existing filters before creating new ones')
    parser.add_argument('--migrate-labels', nargs=2, metavar=('FROM_LABEL', 'TO_LABEL'),
                       help='Migrate emails from one label to another')
    parser.add_argument('--delete-labels', nargs='+', metavar='LABEL_NAME',
                       help='Delete specified labels')
    parser.add_argument('--scan-emails', action='store_true',
                       help='Scan and auto-label existing emails')
    parser.add_argument('--max-emails', type=int, default=1000,
                       help='Maximum emails to process during scanning (default: 1000)')
    parser.add_argument('--days-back', type=int, default=30,
                       help='How many days back to scan emails (0 = all emails, default: 30)')
    parser.add_argument('--debug-categorization', action='store_true',
                       help='Show detailed categorization scoring for debugging')
    parser.add_argument('--cleanup', action='store_true',
                       help='Remove all automation labels and filters (with confirmation)')
    parser.add_argument('--reset', action='store_true',
                       help='Complete reset - remove all automation changes (requires RESET confirmation)')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts for cleanup/reset operations')
    parser.add_argument('--diagnose', action='store_true',
                       help='Diagnose label visibility issues in Gmail web interface')
    parser.add_argument('--fix-visibility', action='store_true',
                       help='Fix label visibility settings to ensure labels appear in Gmail')

    # ML-specific options
    parser.add_argument('--disable-ml', action='store_true',
                       help='Disable ML categorization and use only rule-based approach')
    parser.add_argument('--train-ml', action='store_true',
                       help='Train ML model using existing labeled emails')
    parser.add_argument('--ml-info', action='store_true',
                       help='Show ML model information and statistics')
    parser.add_argument('--bootstrap-training', action='store_true',
                       help='Create synthetic training data to bootstrap ML model')
    parser.add_argument('--add-training-sample', nargs=2, metavar=('EMAIL_ID', 'CATEGORY'),
                       help='Add a specific email as training data for the given category')

    # Concurrent processing options
    parser.add_argument('--concurrent', action='store_true',
                       help='Use concurrent processing for improved performance')
    parser.add_argument('--max-workers', type=int, default=3,
                       help='Maximum number of worker threads for concurrent processing (default: 3)')

    args = parser.parse_args()

    # Initialize automation
    automation = GmailAutomation(args.credentials, args.token, use_ml=not args.disable_ml)

    # Validate and authenticate
    if not automation.validate_environment() or not automation.authenticate():
        return 1

    # Handle cleanup operations first (destructive operations)
    if args.reset:
        success = automation.reset_gmail_to_default(args.force)
        return 0 if success else 1

    if args.cleanup:
        labels_deleted, filters_deleted = automation.cleanup_automation_labels_and_filters(args.force)
        print(f"\nCleanup completed: {labels_deleted} labels and {filters_deleted} filters removed")
        return 0

    # Handle diagnostic operations
    if args.diagnose:
        diagnosis = automation.diagnose_label_visibility()
        if diagnosis.get('recommendations'):
            print(f"\n💡 Recommendations:")
            for rec in diagnosis['recommendations']:
                print(f"   • {rec}")
        return 0

    if args.fix_visibility:
        fixed, failed = automation.fix_label_visibility()
        print(f"\nVisibility fix completed: {fixed} labels fixed, {failed} failed")
        return 0 if failed == 0 else 1

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
                print("⚠️ No synthetic data could be generated")
        else:
            print("⚠️ ML categorization is not enabled")
        return 0

    if args.train_ml:
        if automation.use_ml and automation.ml_categorizer:
            print("🔄 Training ML model from existing labeled emails...")
            # This would collect training data from already labeled emails
            print("⚠️ Feature not fully implemented yet. Use --bootstrap-training first.")
        else:
            print("⚠️ ML categorization is not enabled")
        return 0

    # Handle individual operations
    if args.scan_promos:
        automation.scan_promotional_emails()
        return 0

    if args.clear_filters:
        deleted = automation.clear_existing_filters()
        print(f"\nCleared {deleted} existing filters")
        return 0

    if args.migrate_labels:
        from_label, to_label = args.migrate_labels
        migrated = automation.migrate_emails_to_label([from_label], to_label)
        print(f"\nMigrated {migrated} emails from '{from_label}' to '{to_label}'")
        return 0

    if args.delete_labels:
        deleted, failed = automation.delete_labels(args.delete_labels)
        print(f"\nDeleted {deleted} labels, Failed: {failed}")
        return 0 if failed == 0 else 1

    if args.scan_emails:
        if args.concurrent:
            print("🚀 Using concurrent processing for improved performance...")
            stats = automation.scan_and_label_emails_concurrent(
                args.max_emails,
                args.days_back,
                args.debug_categorization,
                args.max_workers
            )
        else:
            stats = automation.scan_and_label_emails(args.max_emails, args.days_back, args.debug_categorization)

        if 'error' in stats:
            print(f"\nEmail scanning failed: {stats['error']}")
            return 1
        else:
            print(f"\nEmail scanning completed: {stats.get('labeled', 0)} emails labeled")
            return 0

    if args.labels_only:
        created, exists, failed = automation.create_labels()
        print(f"\nLabels - Created: {created}, Existed: {exists}, Failed: {failed}")
        return 0 if failed == 0 else 1

    if args.filters_only:
        # Clear existing filters if requested
        if args.clear_filters:
            automation.clear_existing_filters()

        created, failed = automation.create_filters()
        print(f"\nFilters - Created: {created}, Failed: {failed}")
        return 0 if failed == 0 else 1

    # Run full automation
    success = automation.run_full_automation()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())