
#!/usr/bin/env python3
"""
Gmail Inbox Scanner and Sorter

This script scans all existing emails in a Gmail account based on a
predefined set of filter criteria. It then applies the appropriate
labels to all matching emails in efficient batches.
"""

import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# NEW SCOPE: This is a powerful permission to read and modify your emails.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# --- Filter definitions from the previous script ---
FILTERS_TO_SCAN = [
    {
        'label_name': '🏦 Banking & Finance',
        'criteria': {
            'from_': '{hdfcbank.com OR icicibank.com OR axisbank.com OR sbi.co.in OR kotak.com OR idfcfirstbank.com OR americanexpress.com OR rbi.org.in OR npci.org.in}',
            'has_the_words': '{"statement" OR "transaction alert" OR "credit card" OR "debit card" OR OTP OR payment OR credit OR debit OR EMI}'
        }
    },
    {
        'label_name': '📈 Investments & Trading',
        'criteria': {
            'from_': '{zerodha.com OR groww.in OR indmoney.com OR kuvera.in OR upstox.com OR angelone.in OR camsonline.com OR kfintech.com}',
            'has_the_words': '{"contract note" OR "trade confirmation" OR "mutual fund" OR demat OR SIP OR "portfolio statement"}'
        }
    },
    {
        'label_name': '🛒 Shopping & Orders',
        'criteria': {
            'from_': '{amazon.in OR flipkart.com OR myntra.com OR ajio.com OR nykaa.com OR tatacliq.com OR blinkit.com OR zepto.com}',
            'subject': '{"your order" OR shipped OR delivery OR invoice OR "order confirmation" OR "tracking number" OR "out for delivery"}'
        }
    },
    {
        'label_name': '📦 Receipts & Archive',
        'criteria': {
            'from_': '{uber.com OR ola.in OR makemytrip.com OR goibibo.com OR irctc.co.in OR bookmyshow.com OR swiggy.in OR zomato.com OR dunzo.com OR indigo.com OR airindia.in OR vistara.com OR netflix.com OR primevideo.com OR hotstar.com OR spotify.com OR bescom.in}',
            'has_the_words': '{receipt OR invoice OR "booking confirmation" OR ticket OR e-ticket OR bill OR subscription OR "payment successful"}'
        }
    },
    {
        'label_name': '📰 Marketing & News',
        'criteria': {
            'from_': '{substack.com OR medium.com OR timesofindia.com OR thehindu.com}',
            'has_the_words': '{unsubscribe OR newsletter OR promotion OR discount OR sale OR "daily digest" OR "weekly update"}'
        }
    },
    {
        'label_name': '🔔 Alerts & Security',
        'criteria': {
            'has_the_words': '{"security alert" OR "password reset" OR "login attempt" OR "sign-in attempt" OR 2FA OR "2-Step Verification" OR "suspicious activity"}'
        }
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
    token_file = 'token_sorter.json' # Using a new token file for this script
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
    """Main function to scan and sort all existing emails."""
    print("Gmail Inbox Scanner and Sorter")
    print("==============================")
    service = authenticate_gmail()

    print("\nFetching labels...")
    results = service.users().labels().list(userId='me').execute()
    label_map = {l['name']: l['id'] for l in results.get('labels', [])}
    print(f"Found {len(label_map)} labels.")

    print("\nStarting scan... This may take a while for large inboxes.")
    print("-" * 50)

    for f in FILTERS_TO_SCAN:
        label_name = f['label_name']
        query = build_criteria_query(f['criteria'])
        label_id_to_add = label_map.get(label_name)

        if not label_id_to_add:
            print(f"Skipping filter for '{label_name}' - Label not found.")
            continue
            
        print(f"\nProcessing filter for label: '{label_name}'")
        print(f"  - Query: {query}")

        try:
            # 1. Search for all messages matching the query
            all_message_ids = []
            request = service.users().messages().list(userId='me', q=query)
            
            while request is not None:
                response = request.execute()
                messages = response.get('messages', [])
                if messages:
                    all_message_ids.extend([msg['id'] for msg in messages])
                request = service.users().messages().list_next(request, response)

            if not all_message_ids:
                print("  - Found 0 matching messages.")
                continue
                
            print(f"  - Found {len(all_message_ids)} matching messages. Applying labels in batches...")

            # 2. Apply labels in batches of 100 to be efficient
            batch_size = 100
            for i in range(0, len(all_message_ids), batch_size):
                batch_ids = all_message_ids[i:i + batch_size]
                batch_body = {
                    'ids': batch_ids,
                    'addLabelIds': [label_id_to_add]
                }
                service.users().messages().batchModify(userId='me', body=batch_body).execute()
                print(f"    - Applied label to batch {i//batch_size + 1}...")
                time.sleep(1) # Be kind to the API

            print(f"  ✓ Finished applying label '{label_name}'.")

        except HttpError as error:
            print(f"  ✗ An error occurred: {error}")

    print("\n==============================")
    print("🎉 Scan and sort complete!")

if __name__ == '__main__':
    main()
