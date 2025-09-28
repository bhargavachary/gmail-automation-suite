#!/usr/bin/env python3
"""
Fix Label System Mismatch - Convert Extended Labels to Consolidated Labels

This utility fixes the issue where cluster review corrections were made using
extended 10-category labels but the system is configured for consolidated 6-category labels.
"""

import json
import os
from pathlib import Path

# Label mapping from extended (10 categories) to consolidated (6 categories)
LABEL_MAPPING = {
    # Extended -> Consolidated
    "🏦 Banking & Finance": "🏦 Finance & Bills",
    "📈 Investments & Trading": "🏦 Finance & Bills",
    "🛒 Shopping & Orders": "🛒 Purchases & Receipts",
    "✈️ Travel & Transport": "✈️ Services & Subscriptions",
    "🏥 Insurance & Services": "✈️ Services & Subscriptions",
    "📦 Receipts & Archive": "🛒 Purchases & Receipts",
    "🔔 Alerts & Security": "🔔 Security & Alerts",
    "👤 Personal & Work": "👤 Personal & Social",
    "📰 Marketing & News": "📰 Promotions & Marketing",
    "🎯 Action Required": "👤 Personal & Social",  # Map to Personal as needs attention

    # Already correct consolidated labels (no change needed)
    "🏦 Finance & Bills": "🏦 Finance & Bills",
    "🛒 Purchases & Receipts": "🛒 Purchases & Receipts",
    "✈️ Services & Subscriptions": "✈️ Services & Subscriptions",
    "🔔 Security & Alerts": "🔔 Security & Alerts",
    "📰 Promotions & Marketing": "📰 Promotions & Marketing",
    "👤 Personal & Social": "👤 Personal & Social"
}

def convert_correction_file(file_path: str) -> bool:
    """Convert extended labels to consolidated labels in correction file"""
    print(f"🔄 Processing: {file_path}")

    try:
        # Read the correction file
        with open(file_path, 'r') as f:
            corrections = json.load(f)

        # Track conversions
        conversions = {}
        converted_count = 0

        # Convert each correction
        for correction in corrections:
            old_category = correction.get('corrected_category', '')
            if old_category in LABEL_MAPPING:
                new_category = LABEL_MAPPING[old_category]
                if old_category != new_category:
                    correction['corrected_category'] = new_category
                    converted_count += 1
                    conversions[old_category] = conversions.get(old_category, 0) + 1

        if converted_count > 0:
            # Create backup
            backup_path = file_path + '.backup'
            os.rename(file_path, backup_path)
            print(f"   📁 Backup created: {backup_path}")

            # Save converted file
            with open(file_path, 'w') as f:
                json.dump(corrections, f, indent=2)

            print(f"   ✅ Converted {converted_count} labels:")
            for old, count in conversions.items():
                new = LABEL_MAPPING[old]
                print(f"      {old} → {new} ({count} corrections)")

            return True
        else:
            print(f"   ✅ No conversions needed - already using consolidated labels")
            return False

    except Exception as e:
        print(f"   ❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix label mismatches"""
    print("🔧 Gmail Automation Suite - Label System Mismatch Fixer")
    print("=" * 60)
    print("Converting extended 10-category labels to consolidated 6-category labels...")
    print()

    # Find all correction files
    corrections_dir = Path("data/corrections")
    if not corrections_dir.exists():
        print("❌ No corrections directory found")
        return 1

    correction_files = list(corrections_dir.glob("*.json"))
    if not correction_files:
        print("❌ No correction files found in data/corrections/")
        return 1

    print(f"📋 Found {len(correction_files)} correction files:")

    # Process each file
    converted_any = False
    for file_path in correction_files:
        if convert_correction_file(str(file_path)):
            converted_any = True

    print()
    if converted_any:
        print("✅ Label conversion completed!")
        print()
        print("💡 Next steps:")
        print("   1. Test the fixed corrections:")
        print("      python3 src/gmail_automation.py --retrain-latest-corrections")
        print("   2. Run a small test:")
        print("      python3 src/gmail_automation.py --scan-emails --max-emails 10")
        print("   3. If successful, delete backup files:")
        print("      rm data/corrections/*.backup")
    else:
        print("✅ All correction files already use consolidated labels!")

    return 0

if __name__ == "__main__":
    exit(main())