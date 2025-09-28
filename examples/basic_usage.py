#!/usr/bin/env python3
"""
Gmail Automation Suite - Basic Usage Examples

This script demonstrates basic usage patterns for the Gmail Automation Suite.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gmail_automation import GmailAutomationUnified

def basic_setup():
    """Basic setup example"""
    print("🚀 Basic Gmail Automation Setup")
    print("=" * 40)

    # Initialize with consolidated label system
    automation = GmailAutomationUnified(
        credentials_file='credentials.json',
        token_file='token.json',
        use_ml=True,
        n_topics=6  # 6 topics for consolidated system
    )

    # Authenticate
    if not automation.authenticate():
        print("❌ Authentication failed")
        return False

    # Set to consolidated system
    automation.labels = automation.default_labels
    print("📋 Using consolidated label system (6 categories)")

    # Create labels
    print("\n🏷️ Creating labels...")
    automation.create_labels()

    return automation

def scan_recent_emails(automation, days=7, max_emails=100):
    """Scan recent emails example"""
    print(f"\n📧 Scanning last {days} days ({max_emails} emails max)")
    print("=" * 50)

    # Configure scanning
    from gmail_automation import IncrementalScanConfig
    config = IncrementalScanConfig(
        max_emails=max_emails,
        days_back=days,
        only_unlabeled=True,
        exclude_system_labels=True
    )

    # Scan and categorize
    automation.scan_and_label_emails_incremental(config)

def demonstrate_ml_features(automation):
    """Demonstrate ML features"""
    print("\n🤖 ML Features Demonstration")
    print("=" * 35)

    if automation.ml_categorizer:
        # Show model info
        info = automation.ml_categorizer.get_model_info()
        print("📊 ML Model Status:")
        for key, value in info.items():
            print(f"   {key}: {value}")
    else:
        print("⚠️ ML categorizer not available")

def main():
    """Main demonstration"""
    print("Gmail Automation Suite - Basic Usage Examples")
    print("=" * 55)

    try:
        # Basic setup
        automation = basic_setup()
        if not automation:
            return 1

        # Scan recent emails
        scan_recent_emails(automation, days=3, max_emails=50)

        # Show ML features
        demonstrate_ml_features(automation)

        print("\n✅ Basic usage demonstration completed!")
        print("\n💡 Next steps:")
        print("   1. Run: python gmail_automation.py --scan-emails --concurrent")
        print("   2. Review: python gmail_automation.py --review-clusters")
        print("   3. Maintain: python gmail_automation.py --scan-unlabeled --days-back 1")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())