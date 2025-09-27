
#!/usr/bin/env python3
"""
Gmail Final Consolidation and Optimization Script (v3)

This script executes a one-time migration to a new, optimized label system.
It is the final, polished version designed for a single, comprehensive run.
"""

import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Master scope to allow all necessary actions for labels, messages, AND filters.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.settings.basic']

# --- DATA DEFINITIONS FROM YOUR OPTIMIZATION PLAN ---

# Phase 1 Plan: Which old labels get merged into a new one.
CONSOLIDATION_PLAN = {
    'Label_19': ['Label_21', 'Label_23'],  # Financial
    'Label_20': ['Label_25'],              # Shopping
    'Label_26': ['Label_22'],              # Bills (from Subscriptions)
    'Label_31': ['Label_28', 'Label_29']   # Personal (from Healthcare, Charity)
}

# Phase 2 Plan: Which labels to delete after consolidation.
LABELS_TO_DELETE = [
    'Label_21', 'Label_23', 'Label_25', 'Label_22', 'Label_28', 'Label_29'
]

# Phase 3 Plan: The new, optimized filters to create.
OPTIMIZED_FILTERS = [
    {"label_id": "Label_19", "name": "Financial", "filters": ["from:(cred.club OR hdfc OR icici OR axis OR indmoney OR nse.co.in OR policybazaar OR zerodha OR groww)", "subject:(payment OR bill OR investment OR trading OR insurance OR credit card)"], "mark_important": True},
    {"label_id": "Label_20", "name": "Shopping", "filters": ["from:(amazon OR flipkart OR swiggy OR zomato OR myntra OR blinkit)", "subject:(order OR delivery OR cashback OR cart)"]},
    {"label_id": "Label_24", "name": "Security", "filters": ["from:(google OR apple) AND subject:(security OR alert OR suspicious)"], "mark_important": True},
    {"label_id": "Label_26", "name": "Bills", "filters": ["from:(jio OR airtel OR apple.com OR netflix OR electricity)", "subject:(bill OR subscription OR renewal OR payment due)"]},
    {"label_id": "Label_27", "name": "News", "filters": ["from:(googlenews OR marketbrew OR groundnews OR economictimes)", "subject:(news OR newsletter OR briefing)"]},
    {"label_id": "Label_30", "name": "Official", "filters": ["from:(income-tax OR incometax OR gov.in OR court)", "subject:(tax OR legal OR government OR notice)"], "mark_important": True},
    {"label_id": "Label_31", "name": "Personal", "filters": ["from:(apnacomplex OR tata1mg OR 1mg OR unicef OR hospital)", "subject:(society OR health OR donation OR medical)"]}
]

def authenticate_gmail():
    """Authenticates with Gmail API and returns the service object."""
    creds = None
    token_file = 'token_final_consolidation.json'
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

def migrate_and_consolidate_labels(service, plan):
    """Phase 1: Finds emails with old labels and re-labels them."""
    print("\n--- Phase 1: Consolidating Emails ---")
    for new_label_id, old_label_ids in plan.items():
        print(f"\nMigrating emails from {old_label_ids} to {new_label_id}...")
        query = " OR ".join([f"label:{label_id}" for label_id in old_label_ids])
        try:
            request = service.users().messages().list(userId='me', q=query, maxResults=500)
            all_message_ids = []
            while request is not None:
                response = request.execute()
                messages = response.get('messages', [])
                if messages: all_message_ids.extend([msg['id'] for msg in messages])
                request = service.users().messages().list_next(request, response)
            
            if not all_message_ids:
                print("  - Found 0 messages to migrate.")
                continue

            print(f"  - Found {len(all_message_ids)} messages. Re-labeling in batches...")
            for i in range(0, len(all_message_ids), 100):
                batch_ids = all_message_ids[i:i + 100]
                batch_body = {'ids': batch_ids, 'addLabelIds': [new_label_id], 'removeLabelIds': old_label_ids}
                service.users().messages().batchModify(userId='me', body=batch_body).execute()
                print(f"    - Processed batch {i//100 + 1}/{ -(-len(all_message_ids)//100) }...")
                time.sleep(1)
            print(f"  ✓ Migration to {new_label_id} complete.")
        except HttpError as error:
            print(f"  ✗ An error occurred during migration: {error}")

def delete_old_labels(service, label_ids_to_delete):
    """Phase 2: Deletes the specified list of now-empty labels."""
    print("\n--- Phase 2: Deleting Redundant Labels ---")
    for label_id in label_ids_to_delete:
        print(f"Deleting label {label_id}...")
        try:
            service.users().labels().delete(userId='me', id=label_id).execute()
            print(f"  ✓ Label {label_id} deleted.")
        except HttpError as error:
            print(f"  ✗ FAILED to delete {label_id}: {error}")

def create_optimized_filters(service, filters_plan):
    """Phase 3: Deletes all old filters and creates the new, optimized set."""
    print("\n--- Phase 3: Rebuilding Filter System ---")
    try:
        existing_filters = service.users().settings().filters().list(userId='me').execute().get('filter', [])
        if existing_filters:
            print(f"Deleting {len(existing_filters)} old filters to start fresh...")
            for f in existing_filters:
                service.users().settings().filters().delete(userId='me', id=f['id']).execute()
            print("  ✓ Old filters deleted.")
    except HttpError as error:
        print(f"  - Warning: Could not delete old filters: {error}")
        
    print("\nCreating new optimized filters...")
    for f_def in filters_plan:
        # The different filter parts are joined with OR for broader matching
        query = " OR ".join([f"({q})" for q in f_def['filters']])
        print(f"Processing filter for: '{f_def['name']}'")
        
        action = {'addLabelIds': [f_def['label_id']]}
        if f_def.get('mark_important'):
            action['addLabelIds'].append('IMPORTANT')
            
        filter_body = {'criteria': {'query': query}, 'action': action}
        
        try:
            result = service.users().settings().filters().create(userId='me', body=filter_body).execute()
            print(f"  ✓ Filter CREATED (ID: {result['id']})")
        except HttpError as error:
            print(f"  ✗ Filter FAILED ({error})")

def main():
    """Main function to execute the full organization plan."""
    print("Gmail Final Consolidation and Optimization Script")
    print("===============================================")
    print("\n⚠️  WARNING: This script will make significant, irreversible changes.")
    print("It will re-label emails, delete old labels, and replace ALL existing filters.")
    
    confirm = input("\nAre you sure you want to proceed? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled by user.")
        return

    service = authenticate_gmail()
    
    # Execute the 3-phase plan in the correct order.
    migrate_and_consolidate_labels(service, CONSOLIDATION_PLAN)
    delete_old_labels(service, LABELS_TO_DELETE)
    create_optimized_filters(service, OPTIMIZED_FILTERS)

    print("\n===============================================")
    print("🎉 Gmail Consolidation and Optimization Complete!")
    print("Your label system has been upgraded and new filters are now active.")

if __name__ == '__main__':
    main()
