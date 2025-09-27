#!/usr/bin/env python3
"""
Gmail Promotional Email Manager

This script scans the inbox for potential promotional emails and provides options
to either move them to the Promotions tab or generate a report of unsubscribe links.
"""

import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# This scope allows reading and modifying emails (to apply labels).
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate_gmail():
    """Authenticates with Gmail API and returns the service object."""
    creds = None
    token_file = 'token_promo_manager.json'
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

def find_promo_emails(service, max_results=200):
    """Finds emails in the primary inbox that contain 'unsubscribe'."""
    query = 'in:inbox unsubscribe -category:{social,promotions}'
    print(f"Searching for up to {max_results} potential promotional emails in your inbox...")
    try:
        response = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = response.get('messages', [])
        return messages
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def move_to_promotions(service, message_ids):
    """Moves messages to the Promotions tab by adding the correct label and removing from inbox."""
    print(f"\nMoving {len(message_ids)} emails to the Promotions tab...")
    body = {
        'ids': message_ids,
        'addLabelIds': ['CATEGORY_PROMOTIONS'],
        'removeLabelIds': ['INBOX']
    }
    try:
        service.users().messages().batchModify(userId='me', body=body).execute()
        print("  ✓ Cleanup complete!")
    except HttpError as error:
        print(f"  ✗ An error occurred during cleanup: {error}")

def generate_unsubscribe_report(service, messages):
    """Fetches unsubscribe links and generates a clickable HTML report."""
    print("\nGenerating unsubscribe report... This may take a moment.")
    unsubscribe_links = {}

    for i, msg in enumerate(messages):
        msg_id = msg['id']
        try:
            # Fetch only the headers to be fast and efficient
            full_message = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['List-Unsubscribe', 'From']).execute()
            headers = full_message.get('payload', {}).get('headers', [])
            
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            list_unsubscribe = next((h['value'] for h in headers if h['name'] == 'List-Unsubscribe'), None)

            if list_unsubscribe:
                # Extract the first http link from the header
                http_link = re.search(r'<(https?://[^>]+)>', list_unsubscribe)
                if http_link:
                    sender_name = sender.split('<')[0].strip().replace('"', '')
                    if sender_name not in unsubscribe_links:
                        unsubscribe_links[sender_name] = http_link.group(1)
            
            print(f"  - Scanned {i + 1}/{len(messages)} emails...", end='\r')

        except HttpError as error:
            print(f"\nCould not process message {msg_id}: {error}")

    # Write the report to an HTML file
    with open('unsubscribe_report.html', 'w') as f:
        f.write('<html><head><title>Unsubscribe Report</title></head><body>')
        f.write('<h1>Unsubscribe Report</h1><ul>')
        if unsubscribe_links:
            for name, link in sorted(unsubscribe_links.items()):
                f.write(f'<li><strong>{name}</strong>: <a href="{link}" target="_blank">Unsubscribe</a></li>')
        else:
            f.write('<li>No direct unsubscribe links found in the scanned emails.</li>')
        f.write('</ul></body></html>')
    
    print(f"\n\n  ✓ Report complete! Open the file 'unsubscribe_report.html' in your browser.")

def main():
    """Main function to find promos and prompt user for action."""
    service = authenticate_gmail()
    promo_messages = find_promo_emails(service)

    if not promo_messages:
        print("No promotional emails found in your primary inbox. You're all set!")
        return

    print(f"\nFound {len(promo_messages)} potential promotional emails.")
    print("\nWhat would you like to do?")
    print("  [1] Auto-Clean: Move all these emails to the 'Promotions' tab.")
    print("  [2] Generate Report: Create a list of unsubscribe links to review manually.")
    
    while True:
        choice = input("Enter your choice (1 or 2): ")
        if choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")

    message_ids = [msg['id'] for msg in promo_messages]

    if choice == '1':
        move_to_promotions(service, message_ids)
    elif choice == '2':
        generate_unsubscribe_report(service, promo_messages)

if __name__ == '__main__':
    main()
