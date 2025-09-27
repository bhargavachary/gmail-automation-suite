#!/usr/bin/env python3
"""
Gmail Label Creator Script (Simplified)

This script creates a predefined set of Gmail labels with the default color
using the Gmail API. Colors can be set manually in the Gmail UI afterwards.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope for label management.
SCOPES = ['https://www.googleapis.com/auth/gmail.labels']

# Simplified Label definitions without color data
LABELS = [
    {'name': '🏦 Banking & Finance'},
    {'name': '📈 Investments & Trading'},
    {'name': '🔔 Alerts & Security'},
    {'name': '🛒 Shopping & Orders'},
    {'name': '👤 Personal & Work'},
    {'name': '📰 Marketing & News'},
    {'name': '🎯 Action Required'},
    {'name': '📦 Receipts & Archive'}
]


def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth 2.0 flow.
    Returns authenticated Gmail service object.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                print("ERROR: credentials.json file not found!")
                return None

            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building Gmail service: {e}")
        return None


def create_label(service, label_name):
    """
    Create a single Gmail label with the default color.
    """
    try:
        # Simplified label body without any color information
        label_body = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        result = service.users().labels().create(userId='me', body=label_body).execute()
        return result.get('id')
    except HttpError as error:
        if error.resp.status == 409:
            return 'EXISTS'
        else:
            print(f"HTTP Error creating label '{label_name}': {error}")
            return None
    except Exception as e:
        print(f"Error creating label '{label_name}': {e}")
        return None


def main():
    """
    Main function to authenticate and create all defined Gmail labels.
    """
    print("Gmail Label Creator")
    print("==================")
    print()

    print("Authenticating with Gmail API...")
    service = authenticate_gmail()

    if not service:
        print("Authentication failed. Exiting.")
        return

    print("Authentication successful!")
    print()

    print("Creating labels...")
    print("-" * 50)

    created_count = 0
    exists_count = 0
    failed_count = 0

    for label in LABELS:
        label_name = label['name']

        print(f"Processing: {label_name}")
        result = create_label(service, label_name)

        if result == 'EXISTS':
            print(f"  ✓ Already exists")
            exists_count += 1
        elif result:
            print(f"  ✓ Created successfully (ID: {result})")
            created_count += 1
        else:
            print(f"  ✗ Failed to create")
            failed_count += 1
        print()

    print("=" * 50)
    print("SUMMARY")
    print("==================")
    print(f"Labels created: {created_count}")
    print(f"Already existed: {exists_count}")
    print(f"Failed: {failed_count}")
    print(f"Total processed: {len(LABELS)}")

    if failed_count == 0:
        print("\n🎉 All labels processed successfully!")
    else:
        print(f"\n⚠️  {failed_count} labels failed to create. Check the output above for details.")


if __name__ == '__main__':
    main()
