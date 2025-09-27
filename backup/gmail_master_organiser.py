#!/usr/bin/env python3
"""
Gmail Master Organizer Script

This script executes a comprehensive, data-driven plan to organize a Gmail account.
It ensures labels exist, creates detailed filters, and retroactively applies
labels to existing mail, all based on a predefined priority order.
"""

import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Master scope to allow all necessary actions.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.settings.basic']

# --- DATA DEFINITIONS (from your plan) ---

LABEL_DEFINITIONS = {
    "Banking & Credit Cards": "Label_19",
    "E-commerce & Food Delivery": "Label_20",
    "Investments & Trading": "Label_21",
    "Subscriptions & Services": "Label_22",
    "Insurance & Financial Services": "Label_23",
    "E-commerce Orders": "Label_25",
    "Telecom & Utilities": "Label_26",
    "News & Information": "Label_27",
    "Healthcare & Lifestyle": "Label_28",
    "Charity & Donations": "Label_29",
    "Government & Legal": "Label_30",
    "Housing & Society": "Label_31"
}

IMMEDIATE_LABELING_RULES = [
    {"sender": "CRED", "filter_query": "from:cred.club", "label_name": "Banking & Credit Cards", "additional_actions": ["markImportant"], "priority": "high"},
    {"sender": "Amazon Pay India", "filter_query": "from:amazonpay.in", "label_name": "E-commerce & Food Delivery", "priority": "medium"},
    {"sender": "Amazon Orders", "filter_query": "from:amazon.in AND (subject:order OR subject:delivery)", "label_name": "E-commerce Orders", "priority": "medium"},
    {"sender": "Apple", "filter_query": "from:apple.com OR from:email.apple.com", "label_name": "Subscriptions & Services", "priority": "medium"},
    {"sender": "Jio", "filter_query": "from:jio.com OR from:ebill.mobility@jio.com", "label_name": "Telecom & Utilities", "priority": "medium"},
    {"sender": "Swiggy", "filter_query": "from:swiggy.in", "label_name": "E-commerce & Food Delivery", "priority": "medium"},
    {"sender": "Ground News", "filter_query": "from:groundnews.app", "label_name": "News & Information", "priority": "low"},
    {"sender": "HDFC Bank", "filter_query": "from:hdfcbank.net OR from:hdfcbank.com", "label_name": "Banking & Credit Cards", "priority": "medium"},
    {"sender": "INDmoney", "filter_query": "from:indmoney.com OR from:transactions.indmoney.com", "label_name": "Investments & Trading", "additional_actions": ["markImportant"], "priority": "high"},
    {"sender": "NSE", "filter_query": "from:nse.co.in", "label_name": "Investments & Trading", "additional_actions": ["markImportant"], "priority": "high"},
    {"sender": "Policybazaar", "filter_query": "from:policybazaar.com", "label_name": "Insurance & Financial Services", "priority": "medium"},
    {"sender": "Google News", "filter_query": "from:googlenews-noreply@google.com", "label_name": "News & Information", "priority": "low"},
    {"sender": "Market Brew", "filter_query": "from:marketbrew.in", "label_name": "News & Information", "priority": "low"},
    {"sender": "ApnaComplex", "filter_query": "from:apnacomplex.com", "label_name": "Housing & Society", "priority": "low"}
]

SEARCH_AND_LABEL_RULES = [
    {"sender": "Tata1mg", "search_query": "from:(tata1mg OR 1mg OR netmeds)", "label_name": "Healthcare & Lifestyle", "priority": "medium"},
    {"sender": "Airtel", "search_query": "from:(airtel OR bharti)", "label_name": "Telecom & Utilities", "priority": "medium"},
    {"sender": "Income Tax", "search_query": "from:(income-tax OR incometaxindiaefiling OR cleartax)", "label_name": "Government & Legal", "additional_actions": ["markImportant"], "priority": "high"},
    {"sender": "UNICEF", "search_query": "from:(unicef OR donation)", "label_name": "Charity & Donations", "priority": "low"}
]

PRIORITY_ORDER = ['high', 'medium', 'low']


def authenticate_gmail():
    """Authenticates with Gmail API and returns the service object."""
    creds = None
    token_file = 'token_master_organizer.json'
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

def ensure_labels_exist(service, label_names):
    """Ensures all specified labels exist, creating them if necessary. Returns a name->ID map."""
    print("\n--- Ensuring all required labels exist ---")
    results = service.users().labels().list(userId='me').execute()
    existing_labels = {l['name']: l['id'] for l in results.get('labels', [])}
    
    for name in label_names:
        if name not in existing_labels:
            print(f"Label '{name}' not found. Creating it...")
            try:
                label_body = {'name': name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                created_label = service.users().labels().create(userId='me', body=label_body).execute()
                existing_labels[name] = created_label['id']
                print(f"  ✓ Created label '{name}' with ID {created_label['id']}")
            except HttpError as error:
                print(f"  ✗ FAILED to create label '{name}': {error}")
    
    print("All labels are present.")
    return existing_labels

def create_filters(service, rules, label_map, existing_queries):
    """Creates Gmail filters based on a list of rules."""
    for rule in rules:
        query = rule['filter_query']
        label_name = rule['label_name']
        print(f"\nProcessing filter for: '{rule['sender']}'")
        print(f"  - Query: {query}")

        if query in existing_queries:
            print("  - Status: SKIPPED (Filter with this query already exists)")
            continue
            
        label_id = label_map.get(label_name)
        if not label_id:
            print(f"  - Status: FAILED (Label '{label_name}' not found in map)")
            continue

        action = {'addLabelIds': [label_id]}
        if "markImportant" in rule.get("additional_actions", []):
            action['addLabelIds'].append('IMPORTANT')
            
        filter_body = {'criteria': {'query': query}, 'action': action}
        
        try:
            result = service.users().settings().filters().create(userId='me', body=filter_body).execute()
            print(f"  - Status: CREATED (ID: {result['id']})")
        except HttpError as error:
            print(f"  - Status: FAILED ({error})")

def search_and_apply_labels(service, rules, label_map):
    """Searches for existing emails and applies labels in batches."""
    for rule in rules:
        query = rule['search_query']
        label_name = rule['label_name']
        print(f"\nSearching and applying labels for: '{rule['sender']}'")
        print(f"  - Query: {query}")
        
        label_id_to_add = label_map.get(label_name)
        if not label_id_to_add:
            print(f"  - Status: FAILED (Label '{label_name}' not found in map)")
            continue

        add_labels = [label_id_to_add]
        if "markImportant" in rule.get("additional_actions", []):
            add_labels.append('IMPORTANT')
        
        try:
            request = service.users().messages().list(userId='me', q=query)
            all_message_ids = []
            while request is not None:
                response = request.execute()
                messages = response.get('messages', [])
                if messages: all_message_ids.extend([msg['id'] for msg in messages])
                request = service.users().messages().list_next(request, response)
            
            if not all_message_ids:
                print("  - Found 0 matching messages.")
                continue
                
            print(f"  - Found {len(all_message_ids)} messages. Applying labels in batches...")
            
            for i in range(0, len(all_message_ids), 100):
                batch_ids = all_message_ids[i:i + 100]
                batch_body = {'ids': batch_ids, 'addLabelIds': add_labels}
                service.users().messages().batchModify(userId='me', body=batch_body).execute()
                print(f"    - Labeled batch {i//100 + 1}...")
                time.sleep(1)
            
            print(f"  ✓ Finished applying labels for '{rule['sender']}'.")
        except HttpError as error:
            print(f"  ✗ An error occurred: {error}")

def main():
    """Main function to execute the full organization plan."""
    print("Gmail Master Organizer")
    print("======================")
    service = authenticate_gmail()

    label_name_to_id_map = ensure_labels_exist(service, LABEL_DEFINITIONS.keys())
    
    print("\nFetching existing filters...")
    results = service.users().settings().filters().list(userId='me').execute()
    existing_queries = {f['criteria'].get('query', '') for f in results.get('filter', [])}
    print(f"Found {len(existing_queries)} existing filters.")

    for priority in PRIORITY_ORDER:
        print(f"\n--- Processing {priority.upper()} PRIORITY tasks ---")
        
        # Filter rules for the current priority
        filters_to_run = [r for r in IMMEDIATE_LABELING_RULES if r['priority'] == priority]
        searches_to_run = [r for r in SEARCH_AND_LABEL_RULES if r['priority'] == priority]
        
        if filters_to_run:
            print(f"\n-- Creating {priority} priority filters --")
            create_filters(service, filters_to_run, label_name_to_id_map, existing_queries)
        
        if searches_to_run:
            print(f"\n-- Searching & labeling for {priority} priority rules --")
            search_and_apply_labels(service, searches_to_run, label_name_to_id_map)

    print("\n======================")
    print("🎉 Gmail Master Organization Plan Complete!")

if __name__ == '__main__':
    main()
