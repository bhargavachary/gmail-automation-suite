#!/usr/bin/env python3
"""
Gmail Automation Suite - Classification Preview Tool

This tool helps you understand how the classification system works
before applying it to your Gmail account.
"""

import sys
import os
import json
from collections import Counter

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def show_classification_examples():
    """Show how the classification system categorizes different types of emails"""
    print("🤖 Gmail Classification System Preview")
    print("=" * 50)

    # Load bootstrap training data to show examples
    bootstrap_files = [
        'data/bootstrap/consolidated_bootstrap_training_6_categories.json',
        'data/bootstrap/extended_bootstrap_training_10_categories.json'
    ]

    for file_path in bootstrap_files:
        if os.path.exists(file_path):
            print(f"\n📁 Loading examples from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Group by category
            categories = {}
            for item in data:
                category = item['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(item)

            # Show examples for each category
            system_type = "6-Category Consolidated" if "6_categories" in file_path else "10-Category Extended"
            print(f"\n🏷️ {system_type} System Examples:")
            print("-" * 60)

            for category, items in sorted(categories.items()):
                print(f"\n{category} ({len(items)} examples)")
                print("   Example emails that will be categorized here:")

                for i, item in enumerate(items[:2]):  # Show first 2 examples
                    sender = item['email_data'].get('sender', 'Unknown')
                    subject = item['email_data'].get('subject', 'No subject')
                    print(f"   {i+1}. From: {sender}")
                    print(f"      Subject: {subject}")

                if len(items) > 2:
                    print(f"      ... and {len(items) - 2} more similar emails")

            # Show distribution
            distribution = Counter([item['category'] for item in data])
            print(f"\n📊 Category Distribution ({len(data)} total examples):")
            for category, count in sorted(distribution.items()):
                percentage = (count / len(data)) * 100
                print(f"   {category}: {count} examples ({percentage:.1f}%)")

def show_categorization_rules():
    """Show the rule-based categorization logic"""
    print("\n🧠 How Email Categorization Works")
    print("=" * 40)

    rules = {
        "🏦 Finance & Bills": [
            "Keywords: debited, credited, statement, e-bill, due date, transaction, payment due, bank, invoice, bill",
            "Senders: *bank.com, *axisbank.com, *hdfcbank.net, jio.com, incometax.gov.in",
            "Examples: Bank alerts, credit card statements, phone bills, tax documents"
        ],
        "🛒 Purchases & Receipts": [
            "Keywords: order placed, shipped, delivered, receipt, tax invoice, purchase, amazon, flipkart",
            "Senders: amazon.*, flipkart.*, swiggy.*, myntra.*, apple.com",
            "Examples: E-commerce orders, food delivery, shopping receipts, refunds"
        ],
        "✈️ Services & Subscriptions": [
            "Keywords: booking confirmation, ticket, pnr, subscription renewal, membership, netflix, spotify",
            "Senders: netflix.com, makemytrip.*, 1mg.com, policybazaar.*, oyo.*",
            "Examples: Travel bookings, streaming services, insurance, health services"
        ],
        "🔔 Security & Alerts": [
            "Keywords: new sign in, security alert, verify account, suspicious activity, password change",
            "Senders: security@*, no-reply@dropbox.*, appleid.apple.com, *security*",
            "Examples: Login alerts, security notifications, account verifications"
        ],
        "📰 Promotions & Marketing": [
            "Keywords: unsubscribe, don't miss out, festive offer, pre-approved, newsletter, marketing",
            "Senders: *marketing*, newsletter@*, offers@*, information@*",
            "Examples: Sales emails, newsletters, promotional offers, loan offers"
        ],
        "👤 Personal & Social": [
            "Keywords: gentle reminder, commented on, mentioned you, sent message, invitation, personal",
            "Senders: *linkedin*, *facebook*, calendar-notification@*, invitations@*",
            "Examples: Social media notifications, personal emails, calendar invites"
        ]
    }

    for category, details in rules.items():
        print(f"\n{category}")
        for detail in details:
            print(f"   • {detail}")

def simulate_email_classification():
    """Simulate classification of sample emails"""
    print("\n🎯 Classification Simulation")
    print("=" * 35)

    sample_emails = [
        {
            "sender": "alerts@axisbank.com",
            "subject": "INR 500.00 was debited from your A/c no. XX1234",
            "snippet": "Transaction successful. Available balance: INR 25,000"
        },
        {
            "sender": "order-update@amazon.in",
            "subject": "Your order has been shipped",
            "snippet": "Your order #123-456-789 containing iPhone 15 has been shipped"
        },
        {
            "sender": "no-reply@dropbox.com",
            "subject": "New sign in to your Dropbox account",
            "snippet": "A new device signed into your account from Mumbai, India"
        },
        {
            "sender": "offers@flipkart.com",
            "subject": "Big Billion Days Sale: Up to 80% off",
            "snippet": "Don't miss out on the biggest sale of the year. Unsubscribe anytime"
        }
    ]

    # Simple rule-based classification simulation
    def classify_email(email):
        content = f"{email['sender']} {email['subject']} {email['snippet']}".lower()

        if any(kw in content for kw in ['debited', 'credited', 'bank', 'transaction', 'statement']):
            return "🏦 Finance & Bills"
        elif any(kw in content for kw in ['order', 'shipped', 'delivered', 'amazon', 'flipkart']):
            return "🛒 Purchases & Receipts"
        elif any(kw in content for kw in ['booking', 'ticket', 'subscription', 'netflix']):
            return "✈️ Services & Subscriptions"
        elif any(kw in content for kw in ['sign in', 'security', 'verify', 'dropbox', 'password']):
            return "🔔 Security & Alerts"
        elif any(kw in content for kw in ['offer', 'sale', 'unsubscribe', 'marketing', 'newsletter']):
            return "📰 Promotions & Marketing"
        else:
            return "👤 Personal & Social"

    print("Sample emails and their predicted classifications:")
    print("-" * 55)

    for i, email in enumerate(sample_emails, 1):
        category = classify_email(email)
        print(f"\n{i}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   📧 Snippet: {email['snippet'][:60]}...")
        print(f"   🏷️ Predicted Category: {category}")

def show_system_comparison():
    """Compare consolidated vs extended label systems"""
    print("\n⚖️  Label System Comparison")
    print("=" * 35)

    print("📋 CONSOLIDATED SYSTEM (6 categories) - Recommended for most users:")
    consolidated = [
        "🏦 Finance & Bills - All financial transactions, bills, banking",
        "🛒 Purchases & Receipts - All shopping, orders, receipts",
        "✈️ Services & Subscriptions - Travel, subscriptions, services",
        "🔔 Security & Alerts - Security notifications, alerts",
        "📰 Promotions & Marketing - Marketing, newsletters, offers",
        "👤 Personal & Social - Personal communication, social media"
    ]

    for item in consolidated:
        print(f"   • {item}")

    print("\n📋 EXTENDED SYSTEM (10 categories) - For advanced users:")
    extended = [
        "🏦 Banking & Finance - Bank transactions, statements",
        "📈 Investments & Trading - Stocks, mutual funds, SIPs",
        "🛒 Shopping & Orders - E-commerce lifecycle",
        "✈️ Travel & Transport - Flights, hotels, transport",
        "🏥 Insurance & Services - Insurance, healthcare",
        "📦 Receipts & Archive - Subscriptions, confirmations",
        "🔔 Alerts & Security - Security alerts, urgent notifications",
        "👤 Personal & Work - Personal and work communications",
        "📰 Marketing & News - Marketing campaigns, newsletters",
        "🎯 Action Required - Emails needing immediate attention"
    ]

    for item in extended:
        print(f"   • {item}")

    print("\n💡 Recommendation:")
    print("   • Start with CONSOLIDATED (6 categories) for simplicity")
    print("   • Upgrade to EXTENDED (10 categories) if you need more granular control")
    print("   • You can switch between systems anytime")

def main():
    """Main function to run the classification preview"""
    print("🔍 Gmail Automation Suite - Classification Preview")
    print("=" * 60)
    print("This tool shows you how emails will be categorized before applying to your Gmail account.\n")

    try:
        show_classification_examples()
        show_categorization_rules()
        simulate_email_classification()
        show_system_comparison()

        print("\n" + "=" * 60)
        print("✅ Classification Preview Complete!")
        print("\n💡 Next Steps:")
        print("   1. Review the classifications above")
        print("   2. Choose between consolidated (6) or extended (10) categories")
        print("   3. Run reset procedure if you want to start fresh")
        print("   4. Apply the classification system to your Gmail account")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())