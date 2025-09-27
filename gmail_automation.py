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

    def categorize_email(self, email_data: Dict) -> Optional[str]:
        """
        Categorize an email based on sender, subject, and content patterns.
        Returns the appropriate label name or None if no category matches.
        """
        sender = email_data.get('sender', '').lower()
        subject = email_data.get('subject', '').lower()
        snippet = email_data.get('snippet', '').lower()

        # Banking & Finance patterns
        banking_domains = [
            'hdfcbank.com', 'icicibank.com', 'axisbank.com', 'sbi.co.in', 'kotak.com',
            'americanexpress.com', 'cred.club', 'paytm.com', 'phonepe.com', 'googlepay.com'
        ]
        banking_keywords = [
            'statement', 'transaction', 'credit card', 'debit card', 'otp', 'payment',
            'bank', 'account', 'balance', 'emi', 'loan', 'credit', 'debit'
        ]

        if (any(domain in sender for domain in banking_domains) or
            any(keyword in subject + snippet for keyword in banking_keywords)):
            return '🏦 Banking & Finance'

        # Investments & Trading patterns
        investment_domains = [
            'zerodha.com', 'groww.in', 'upstox.com', 'angelone.in', 'kfintech.com',
            'camsonline.com', 'indmoney.com', 'kuvera.in'
        ]
        investment_keywords = [
            'contract note', 'mutual fund', 'demat', 'sip', 'portfolio', 'investment',
            'trading', 'shares', 'stock', 'dividend', 'nfo', 'nav'
        ]

        if (any(domain in sender for domain in investment_domains) or
            any(keyword in subject + snippet for keyword in investment_keywords)):
            return '📈 Investments & Trading'

        # Security & Alerts patterns
        security_keywords = [
            'security alert', 'suspicious activity', 'login attempt', 'password',
            'verification', 'two-factor', '2fa', 'unauthorized', 'breach'
        ]
        security_senders = ['google', 'apple', 'microsoft', 'security', 'noreply']

        if (any(keyword in subject + snippet for keyword in security_keywords) or
            any(word in sender for word in security_senders) and 'security' in subject + snippet):
            return '🔔 Alerts & Security'

        # Shopping & Orders patterns
        shopping_domains = [
            'amazon.in', 'flipkart.com', 'myntra.com', 'ajio.com', 'nykaa.com',
            'tatacliq.com', 'meesho.com', 'snapdeal.com'
        ]
        shopping_keywords = [
            'order', 'delivery', 'shipped', 'tracking', 'invoice', 'receipt',
            'purchase', 'cart', 'checkout', 'payment successful'
        ]

        if (any(domain in sender for domain in shopping_domains) or
            any(keyword in subject + snippet for keyword in shopping_keywords)):
            return '🛒 Shopping & Orders'

        # Travel & Transport patterns
        travel_domains = [
            'makemytrip.com', 'goibibo.com', 'irctc.co.in', 'indigo.com', 'airindia.in',
            'vistara.com', 'uber.com', 'ola.in', 'booking.com', 'agoda.com'
        ]
        travel_keywords = [
            'ticket', 'booking', 'pnr', 'flight', 'train', 'hotel', 'travel',
            'itinerary', 'boarding', 'reservation'
        ]

        if (any(domain in sender for domain in travel_domains) or
            any(keyword in subject + snippet for keyword in travel_keywords)):
            return '✈️ Travel & Transport'

        # Insurance & Services patterns
        insurance_domains = [
            'policybazaar.com', 'acko.com', 'hdfcergo.com', 'digitinsurance.com',
            'tata1mg.com', '1mg.com'
        ]
        insurance_keywords = [
            'policy', 'premium', 'renewal', 'claim', 'insurance', 'health',
            'medical', 'doctor', 'hospital', 'pharmacy'
        ]

        if (any(domain in sender for domain in insurance_domains) or
            any(keyword in subject + snippet for keyword in insurance_keywords)):
            return '🏥 Insurance & Services'

        # Receipts & Archive patterns
        receipt_domains = [
            'netflix.com', 'primevideo.com', 'hotstar.com', 'spotify.com',
            'swiggy.in', 'zomato.com', 'bookmyshow.com', 'dunzo.com'
        ]
        receipt_keywords = [
            'receipt', 'invoice', 'bill', 'subscription', 'renewal', 'payment successful',
            'order delivered', 'booking confirmation'
        ]

        if (any(domain in sender for domain in receipt_domains) or
            any(keyword in subject + snippet for keyword in receipt_keywords)):
            return '📦 Receipts & Archive'

        # Marketing & News patterns
        news_keywords = [
            'newsletter', 'unsubscribe', 'news', 'update', 'briefing',
            'marketing', 'promotional', 'offer', 'deal', 'sale'
        ]

        if any(keyword in subject + snippet for keyword in news_keywords):
            return '📰 Marketing & News'

        # Personal & Work patterns (catch-all for internal/personal emails)
        work_keywords = [
            'meeting', 'project', 'deadline', 'report', 'document',
            'colleague', 'team', 'office', 'work'
        ]

        if any(keyword in subject + snippet for keyword in work_keywords):
            return '👤 Personal & Work'

        return None

    def scan_and_label_emails(self, max_emails: int = 1000, days_back: int = 30) -> Dict[str, int]:
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

                        # Categorize email
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

    if args.scan_emails:
        stats = automation.scan_and_label_emails(args.max_emails, args.days_back)
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