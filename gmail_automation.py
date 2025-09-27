#!/usr/bin/env python3
"""
Gmail Automation Suite - Streamlined & Consolidated

A comprehensive tool for Gmail management that includes:
- Label creation and management with advanced filters
- Smart filter creation with batch processing
- Label consolidation and migration
- Promotional email management
- Inbox organization and cleanup
- Optimized filter system with importance marking

Author: Gmail Automation Suite
Version: 3.0.0
"""

import os
import re
import time
import json
import argparse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.labels_cache = {}

        # Predefined labels with colors
        self.labels = [
            Label('🏦 Banking & Finance', '#4285f4'),
            Label('📈 Investments & Trading', '#0b8043'),
            Label('🔔 Alerts & Security', '#d93025'),
            Label('🛒 Shopping & Orders', '#ff6d01'),
            Label('👤 Personal & Work', '#9c27b0'),
            Label('📰 Marketing & News', '#5f6368'),
            Label('🎯 Action Required', '#ea4335'),
            Label('📦 Receipts & Archive', '#9aa0a6'),
            Label('🏥 Insurance & Services', '#34a853'),
            Label('✈️ Travel & Transport', '#ff9800')
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

    args = parser.parse_args()

    # Initialize automation
    automation = GmailAutomation(args.credentials, args.token)

    # Validate and authenticate
    if not automation.validate_environment() or not automation.authenticate():
        return 1

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