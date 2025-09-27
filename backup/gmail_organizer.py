#!/usr/bin/env python3
"""
Gmail Organization Automation Script (v2)

This script executes a multi-phase plan to enhance a Gmail account:
1.  Renames existing labels for clarity.
2.  Creates new labels for expanded category coverage.
3.  Creates a comprehensive set of new, detailed filters.
4.  Implements auto-archiving for routine notifications.
"""

import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# The master scope to allow all necessary actions.
# The master scope to allow all necessary actions for labels AND filters.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.settings.basic']

# --- PHASE 1: LABELS TO RENAME ---
# Format: { 'label_id_to_find': 'New Label Name' }
LABELS_TO_RENAME = {
    'Label_19': '🏦 Banking & Finance',
    'Label_23': '📈 Investments & Trading',
    'Label_24': '🔒 Security & Alerts' # Renaming from "🔔 Alerts & Security"
}

# --- PHASE 2: NEW LABELS TO CREATE ---
LABELS_TO_CREATE = [
    {'name': '📰 News & Newsletters'},
    {'name': '🏥 Insurance & Services'},
    {'name': '🛒 Shopping & Orders'},
    {'name': '👤 Personal & Work'}
]

# --- PHASE 3 & 4: FILTERS TO CREATE (Including Auto-Archiving) ---
FILTERS_TO_CREATE = [
    # Phase 3: Filter Expansion
    {
        'label_name': '🏥 Insurance & Services',
        'criteria': {
            'from_': '{policybazaar.com OR acko.com OR hdfcergo.com OR digitinsurance.com}',
            'has_the_words': '{policy OR premium OR renewal OR claim}'
        }
    },
    {
        'label_name': '📰 News & Newsletters',
        'criteria': {
            'from_': '{google.com}', # For Google News
            'has_the_words': '{"google news" OR digest OR newsletter}'
        }
    },
    {
        'label_name': '🛒 Shopping & Orders',
        'criteria': {
            'from_': '{amazon.in OR flipkart.com OR myntra.com}'
            # This will be enhanced by the auto-archive filter below
        }
    },
    # Phase 4: Automation Enhancement (Auto-Archiving)
    {
        'label_name': '🏦 Banking & Finance',
        'criteria': {
            'from_': '{hdfcbank.com OR icicibank.com OR axisbank.com}',
            'has_the_words': '{"transaction confirmation" OR "payment received"}'
        },
        'action': {'removeLabelIds': ['INBOX']} # Archive it
    },
    {
        'label_name': '🛒 Shopping & Orders',
        'criteria': {
            'from_': '{amazon.in OR flipkart.com OR swiggy.in OR zomato.com}',
            'subject': '{Delivered OR "has been delivered"}'
        },
        'action': {'removeLabelIds': ['INBOX']} # Archive it
    },
    {
        'label_name': '📰 News & Newsletters',
        'criteria': {
            'has_the_words': 'unsubscribe'
        },
        'action': {'removeLabelIds': ['INBOX']} # Archive old promotional emails
    }
]


def authenticate_gmail():
    """Authenticates with Gmail API and returns the service object."""
    creds = None
    token_file = 'token_organizer.json'
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

def build_criteria_query(criteria):
    """Builds a Gmail query string from a dictionary of criteria."""
    query_parts = []
    if criteria.get('from_'): query_parts.append(f"from:({criteria['from_']})")
    if criteria.get('subject'): query_parts.append(f"subject:({criteria['subject']})")
    if criteria.get('has_the_words'): query_parts.append(f"({criteria['has_the_words']})")
    return ' '.join(query_parts)

def main():
    """Main function to execute the multi-phase organization plan."""
    print("Gmail Organization Automation Script v2")
    print("=======================================")
    service = authenticate_gmail()

    # --- PHASE 1: RENAME LABELS ---
    print("\n--- Phase 1: Renaming Labels ---")
    for label_id, new_name in LABELS_TO_RENAME.items():
        print(f"Renaming {label_id} to '{new_name}'...")
        try:
            update_body = {'name': new_name}
            service.users().labels().patch(userId='me', id=label_id, body=update_body).execute()
            print("  ✓ Success")
        except HttpError as error:
            print(f"  ✗ FAILED: {error}")

    # --- PHASE 2: CREATE NEW LABELS ---
    print("\n--- Phase 2: Creating New Labels ---")
    existing_labels_results = service.users().labels().list(userId='me').execute()
    existing_label_names = [l['name'] for l in existing_labels_results.get('labels', [])]
    
    for label_def in LABELS_TO_CREATE:
        if label_def['name'] in existing_label_names:
            print(f"Label '{label_def['name']}' already exists. Skipping.")
        else:
            print(f"Creating label '{label_def['name']}'...")
            try:
                service.users().labels().create(userId='me', body=label_def).execute()
                print("  ✓ Success")
            except HttpError as error:
                print(f"  ✗ FAILED: {error}")
    
    # --- GET UPDATED LABEL MAP ---
    print("\nFetching updated label map for filter creation...")
    time.sleep(2) # Give a moment for changes to propagate
    results = service.users().labels().list(userId='me').execute()
    label_map = {l['name']: l['id'] for l in results.get('labels', [])}
    print("Label map updated.")

    # --- PHASE 3 & 4: CREATE FILTERS ---
    print("\n--- Phase 3 & 4: Creating New Filters (with Auto-Archiving) ---")
    existing_filters_results = service.users().settings().filters().list(userId='me').execute()
    existing_queries = {f['criteria'].get('query', '') for f in existing_filters_results.get('filter', [])}
    
    for f_def in FILTERS_TO_CREATE:
        query = build_criteria_query(f_def['criteria'])
        label_name = f_def['label_name']
        print(f"\nProcessing filter for label: '{label_name}'")
        print(f"  - Query: {query}")

        if query in existing_queries:
            print("  - Status: SKIPPED (Filter with this query already exists)")
            continue
        
        label_id = label_map.get(label_name)
        if not label_id:
            print(f"  - Status: FAILED (Label '{label_name}' not found)")
            continue
            
        action = f_def.get('action', {})
        action.setdefault('addLabelIds', []).append(label_id)
        
        filter_body = {'criteria': {'query': query}, 'action': action}
        
        try:
            result = service.users().settings().filters().create(userId='me', body=filter_body).execute()
            print(f"  - Status: CREATED (ID: {result['id']})")
        except HttpError as error:
            print(f"  - Status: FAILED ({error})")

    print("\n=======================================")
    print("🎉 Gmail Organization Update Complete!")

if __name__ == '__main__':
    main()
