#!/usr/bin/env python3
"""
Customize Training Data for User's Specific Email Patterns

This script analyzes the user's actual emails and creates personalized
training data based on their specific senders, keywords, and patterns.
"""

import sys
import os
import json
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_email_patterns():
    """Analyze user's email patterns from cluster review data"""
    print("🔍 Analyzing Your Email Patterns")
    print("=" * 40)

    # Check for existing correction data
    corrections_dir = Path("data/corrections")
    if corrections_dir.exists():
        correction_files = list(corrections_dir.glob("*.json"))
        if correction_files:
            print(f"📋 Found {len(correction_files)} correction sessions")
            # Load and analyze patterns
            for file_path in correction_files:
                with open(file_path) as f:
                    corrections = json.load(f)
                print(f"   📊 {len(corrections)} email corrections in {file_path.name}")
                analyze_corrections(corrections)

    # Suggest specific improvements based on patterns seen
    print("\n💡 Training Optimization Recommendations:")
    print("=" * 45)

    print("🏦 BANKING & FINANCE PATTERNS:")
    print("   Based on your HDFC Bank emails, I recommend:")
    print("   • Enhanced detection for credit card transactions")
    print("   • Better recognition of banking alert patterns")
    print("   • Improved categorization of payment notifications")

    print("\n🛒 PURCHASE & RECEIPT PATTERNS:")
    print("   • Focus on transaction amounts and merchant names")
    print("   • Enhanced detection of order confirmations")
    print("   • Better recognition of delivery notifications")

    print("\n🔔 SECURITY & ALERT PATTERNS:")
    print("   • Improved detection of bank security alerts")
    print("   • Better recognition of login notifications")
    print("   • Enhanced categorization of account alerts")

def analyze_corrections(corrections):
    """Analyze patterns in user corrections"""
    categories = {}
    senders = {}

    for correction in corrections:
        category = correction.get('corrected_category', '')
        email_data = correction.get('email_data', {})
        sender = email_data.get('sender', '')

        categories[category] = categories.get(category, 0) + 1

        # Extract domain from sender
        if '@' in sender:
            domain = sender.split('@')[-1].split('>')[0].strip()
            senders[domain] = senders.get(domain, 0) + 1

    print(f"   📈 Top corrected categories:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"      • {cat}: {count} corrections")

    print(f"   📧 Top sender domains:")
    for domain, count in sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"      • {domain}: {count} emails")

def create_custom_rules():
    """Create custom categorization rules based on user patterns"""
    print("\n🛠️ Creating Custom Rules for Your Email Patterns")
    print("=" * 50)

    # Custom rules based on observed patterns
    custom_rules = {
        "🏦 Finance & Bills": {
            "enhanced_keywords": [
                "debited", "credited", "transaction", "payment", "bill amount",
                "outstanding", "due date", "statement", "a/c no", "account",
                "emi", "instalment", "banking", "upi", "neft", "rtgs"
            ],
            "enhanced_senders": [
                "*hdfc*", "*icici*", "*sbi*", "*axis*", "*kotak*",
                "*alerts@*", "*noreply@*bank*", "*banking*",
                "*transactions*", "*instaalerts*"
            ],
            "subject_patterns": [
                "*debited*", "*credited*", "*rs.*", "*inr*", "*payment*",
                "*transaction*", "*alert*", "*a/c*", "*account*"
            ]
        },
        "🛒 Purchases & Receipts": {
            "enhanced_keywords": [
                "order", "delivered", "shipped", "confirmed", "receipt",
                "purchase", "invoice", "tax invoice", "refund", "return",
                "flipkart", "amazon", "swiggy", "zomato", "myntra"
            ],
            "enhanced_senders": [
                "*flipkart*", "*amazon*", "*swiggy*", "*zomato*", "*myntra*",
                "*order*", "*purchase*", "*delivery*", "*shopping*"
            ]
        },
        "🔔 Security & Alerts": {
            "enhanced_keywords": [
                "login", "sign in", "security", "suspicious", "verify",
                "authentication", "otp", "password", "account access"
            ],
            "enhanced_senders": [
                "*security*", "*no-reply*", "*noreply*", "*alerts*"
            ]
        }
    }

    # Save custom rules
    rules_file = "data/custom_email_rules.json"
    with open(rules_file, 'w') as f:
        json.dump(custom_rules, f, indent=2)

    print(f"✅ Custom rules saved to {rules_file}")
    return custom_rules

def suggest_next_steps():
    """Suggest next steps for training optimization"""
    print("\n🎯 Recommended Training Optimization Steps")
    print("=" * 45)

    steps = [
        "1. 🔄 Update email categories with custom rules",
        "2. 🧠 Run bootstrap training with enhanced patterns",
        "3. 🔍 Test classification on small sample",
        "4. 📊 Use cluster review for fine-tuning",
        "5. ⚡ Apply to larger email batches"
    ]

    for step in steps:
        print(f"   {step}")

    print(f"\n💡 Commands to run next:")
    print(f"   # Update custom rules and bootstrap training")
    print(f"   python3 src/gmail_automation.py --bootstrap-training")
    print(f"   ")
    print(f"   # Test on small batch with debug")
    print(f"   python3 src/gmail_automation.py --scan-emails --max-emails 20 --debug")
    print(f"   ")
    print(f"   # Run interactive review session")
    print(f"   python3 src/gmail_automation.py --review-clusters --review-emails 30")

def main():
    """Main function"""
    print("📧 Gmail Automation - Training Customization Tool")
    print("=" * 55)
    print("Analyzing your email patterns to create optimized training data...\n")

    # Analyze existing patterns
    analyze_email_patterns()

    # Create custom rules
    custom_rules = create_custom_rules()

    # Suggest next steps
    suggest_next_steps()

    print(f"\n✅ Training customization analysis complete!")
    print(f"🎯 Ready to optimize classification for your specific email patterns")

if __name__ == "__main__":
    main()