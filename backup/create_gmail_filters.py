#!/usr/bin/env python3
"""
Advanced Gmail Filter Creator Script

This script creates a predefined set of complex Gmail filters using detailed criteria
like sender, subject, and keywords. It automatically maps label names to
their IDs and avoids creating duplicate filters.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# COMBINED SCOPES: Permission for labels and settings.
SCOPES = ['https://www.googleapis.com/auth/gmail.labels', 'https://www.googleapis.com/auth/gmail.settings.basic']

# --- Define the filters with expanded keywords ---
FILTERS_TO_CREATE = [
    {
        'label_name': '🏦 Banking & Finance',
        'criteria': {
            'from_': '{hdfcbank.com OR icicibank.com OR axisbank.com OR sbi.co.in OR kotak.com OR idfcfirstbank.com OR americanexpress.com OR rbi.org.in OR npci.org.in}',
            'has_the_words': '{"statement" OR "transaction alert" OR "credit card" OR "debit card" OR OTP OR payment OR credit OR debit OR EMI}'
        },
        'action': {}
    },
    {
        'label_name': '📈 Investments & Trading',
        'criteria': {
            'from_': '{zerodha.com OR groww.in OR indmoney.com OR kuvera.in OR upstox.com OR angelone.in OR camsonline.com OR kfintech.com}',
            'has_the_words': '{"contract note" OR "trade confirmation" OR "mutual fund" OR demat OR SIP OR "portfolio statement"}'
        },
        'action': {}
    },
    {
        'label_name': '🛒 Shopping & Orders',
        'criteria': {
            'from_': '{amazon.in OR flipkart.com OR myntra.com OR ajio.com OR nykaa.com OR tatacliq.com OR blinkit.com OR zepto.com}',
            'subject': '{"your order" OR shipped OR delivery OR invoice OR "order confirmation" OR "tracking number" OR "out for delivery"}'
        },
        'action': {}
    },
    {
        'label_name': '📦 Receipts & Archive',
        'criteria': {
            'from_': '{uber.com OR ola.in OR makemytrip.com OR goibibo.com OR irctc.co.in OR bookmyshow.com OR swiggy.in OR zomato.com OR dunzo.com OR indigo.com OR airindia.in OR vistara.com OR netflix.com OR primevideo.com OR hotstar.com OR spotify.com OR bescom.in}',
            'has_the_words': '{receipt OR invoice OR "booking confirmation" OR ticket OR e-ticket OR bill OR subscription OR "payment successful"}'
        },
        'action': {
            'removeLabelIds': ['INBOX']  # This archives the email
        }
    },
    {
        'label_name': '📰 Marketing & News',
        'criteria': {
            'from_': '{substack.com OR medium.com OR timesofindia.com OR thehindu.com}',
            'has_the_words': '{unsubscribe OR newsletter OR promotion OR discount OR sale OR "daily digest" OR "weekly update"}'
        },
        'action': {}
    },
    {
        'label_name': '🔔 Alerts & Security',
        'criteria': {
            'has_the_words': '{"security alert" OR "password reset" OR "login attempt" OR "sign-in attempt" OR 2FA OR "2-Step Verification" OR "suspicious activity"}'
        },
        'action': {}
    }
]

def build_criteria_query(criteria):
    """Builds a Gmail query string from a dictionary of criteria."""
    query_parts = []
    if criteria.get('from_'):
        query_parts.append(f"from:({criteria['from_']})")
    if criteria.get('subject'):
        query_parts.append(f"subject:({criteria['subject']})")
    if criteria.get('has_the_words'):
        query_parts.append(f"({criteria['has_the_words']})")
    if criteria.get('does_not_have'):
        query_parts.append(f"-({criteria['does_not_have']})")
    return ' '.join(query_parts)

def authenticate_gmail():
    """Authenticates with Gmail API and returns the service object."""
    creds = None
    # UPDATED: Using token_filters.json as the token file
    token_file = 'token_filters.json'
    
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def main():
    """Main function to create all defined Gmail filters."""
    print("Advanced Gmail Filter Creator")
    print("=============================")
    service = authenticate_gmail()

    # 1. Get all labels and create a name-to-ID map
    print("\nFetching labels...")
    results = service.users().labels().list(userId='me').execute()
    label_map = {l['name']: l['id'] for l in results.get('labels', [])}
    print(f"Found {len(label_map)} labels.")

    # 2. Get all existing filters to avoid duplicates
    print("\nFetching existing filters...")
    results = service.users().settings().filters().list(userId='me').execute()
    existing_filters = results.get('filter', [])
    existing_queries = {f['criteria'].get('query', '') for f in existing_filters}
    print(f"Found {len(existing_filters)} existing filters.")
    
    # 3. Process and create new filters
    print("\nProcessing filters to create...")
    print("-" * 50)
    
    created_count = 0
    skipped_count = 0

    for f in FILTERS_TO_CREATE:
        label_name = f['label_name']
        query = build_criteria_query(f['criteria'])
        
        print(f"Processing filter for label: '{label_name}'")
        print(f"  - Generated Query: {query}")
        
        if query in existing_queries:
            print("  - Status: SKIPPED (A filter with this exact query already exists)")
            skipped_count += 1
            print()
            continue
            
        label_id = label_map.get(label_name)
        if not label_id:
            print(f"  - Status: FAILED (Label '{label_name}' not found)")
            print()
            continue

        action = f.get('action', {})
        action['addLabelIds'] = [label_id]
        
        filter_body = {
            'criteria': {'query': query},
            'action': action
        }
        
        try:
            result = service.users().settings().filters().create(userId='me', body=filter_body).execute()
            print(f"  - Status: CREATED (ID: {result['id']})")
            created_count += 1
        except HttpError as error:
            print(f"  - Status: FAILED ({error})")
        print()

    print("=" * 50)
    print("SUMMARY")
    print("=============================")
    print(f"Filters created: {created_count}")
    print(f"Filters skipped (already exist): {skipped_count}")

if __name__ == '__main__':
    main()
