#!/usr/bin/env python3
"""
Gmail Automation Suite - Streamlined & Consolidated

A comprehensive tool for Gmail management that includes:
- Label creation and management
- Smart filter creation
- Promotional email management
- Inbox organization

Author: Gmail Automation Suite
Version: 2.0.0
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

        # Predefined filters
        self.filters = [
            Filter(
                '🏦 Banking & Finance',
                {
                    'from': 'hdfcbank.com OR icicibank.com OR axisbank.com OR sbi.co.in OR kotak.com OR americanexpress.com',
                    'hasTheWords': 'statement OR "transaction alert" OR "credit card" OR OTP OR payment'
                }
            ),
            Filter(
                '📈 Investments & Trading',
                {
                    'from': 'zerodha.com OR groww.in OR upstox.com OR angelone.in OR kfintech.com',
                    'hasTheWords': '"contract note" OR "mutual fund" OR demat OR SIP OR portfolio'
                }
            ),
            Filter(
                '🛒 Shopping & Orders',
                {
                    'from': 'amazon.in OR flipkart.com OR myntra.com OR ajio.com OR nykaa.com',
                    'subject': '"your order" OR shipped OR delivery OR invoice OR "order confirmation"'
                }
            ),
            Filter(
                '📦 Receipts & Archive',
                {
                    'from': 'uber.com OR swiggy.in OR zomato.com OR bookmyshow.com OR netflix.com',
                    'hasTheWords': 'receipt OR invoice OR "booking confirmation" OR bill OR subscription'
                }
            ),
            Filter(
                '✈️ Travel & Transport',
                {
                    'from': 'makemytrip.com OR goibibo.com OR irctc.co.in OR indigo.com OR airindia.in',
                    'hasTheWords': 'ticket OR "booking confirmation" OR PNR OR "travel itinerary"'
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
                # Prepare filter body
                filter_body = {
                    'criteria': filter_config.criteria,
                    'action': {
                        'addLabelIds': [existing_labels[filter_config.label_name]],
                        'removeLabelIds': ['INBOX']  # Auto-archive
                    }
                }

                # Merge custom actions if provided
                if filter_config.action:
                    filter_body['action'].update(filter_config.action)

                self.service.users().settings().filters().create(
                    userId='me',
                    body=filter_body
                ).execute()

                print(f"  ✅ Filter created successfully")
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

    args = parser.parse_args()

    # Initialize automation
    automation = GmailAutomation(args.credentials, args.token)

    # Validate and authenticate
    if not automation.validate_environment() or not automation.authenticate():
        return 1

    if args.scan_promos:
        automation.scan_promotional_emails()
        return 0

    if args.labels_only:
        created, exists, failed = automation.create_labels()
        print(f"\nLabels - Created: {created}, Existed: {exists}, Failed: {failed}")
        return 0 if failed == 0 else 1

    if args.filters_only:
        created, failed = automation.create_filters()
        print(f"\nFilters - Created: {created}, Failed: {failed}")
        return 0 if failed == 0 else 1

    # Run full automation
    success = automation.run_full_automation()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())