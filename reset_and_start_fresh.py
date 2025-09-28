#!/usr/bin/env python3
"""
Gmail Automation Suite - Complete Reset and Fresh Start Tool

This tool helps you completely reset everything and start fresh with your Gmail automation.
"""

import sys
import os
import json
import shutil
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Try to import Gmail automation for cleanup
try:
    from gmail_automation import GmailAutomationUnified
    GMAIL_CLEANUP_AVAILABLE = True
except ImportError:
    GMAIL_CLEANUP_AVAILABLE = False

def check_gmail_labels():
    """Check what automation labels exist in Gmail"""
    if not GMAIL_CLEANUP_AVAILABLE:
        return None

    try:
        # Initialize automation to check labels
        automation = GmailAutomationUnified()
        if not automation.authenticate():
            return None

        # Get existing automation labels
        existing_labels = automation.get_existing_labels()
        return existing_labels
    except Exception as e:
        print(f"   ⚠️  Could not check Gmail labels: {e}")
        return None

def reset_gmail_labels_and_filters():
    """Remove all automation labels and filters from Gmail"""
    print("\n🏷️ Resetting Gmail Labels and Filters")
    print("=" * 45)

    if not GMAIL_CLEANUP_AVAILABLE:
        print("   ⚠️  Gmail cleanup not available - import error")
        return False

    try:
        # Initialize automation
        automation = GmailAutomationUnified()
        if not automation.authenticate():
            print("   ❌ Gmail authentication failed")
            return False

        # Get existing automation labels
        existing_labels = automation.get_existing_labels()

        if not existing_labels:
            print("   ✅ No automation labels found in Gmail")
            return True

        print(f"   📋 Found {len(existing_labels)} automation labels to remove:")
        for label_name in existing_labels.keys():
            print(f"      • {label_name}")

        # Confirm deletion
        print(f"\n   ❓ Remove all {len(existing_labels)} automation labels from Gmail? (y/N): ", end="")
        confirm = input().strip().lower()

        if confirm not in ['y', 'yes']:
            print("   ❌ Gmail cleanup cancelled")
            return False

        # Remove labels
        removed_count = 0
        for label_name, label_id in existing_labels.items():
            try:
                automation.service.users().labels().delete(
                    userId='me',
                    id=label_id
                ).execute()
                print(f"   🗑️  Removed label: {label_name}")
                removed_count += 1
            except Exception as e:
                print(f"   ⚠️  Could not remove {label_name}: {e}")

        print(f"   ✅ Successfully removed {removed_count}/{len(existing_labels)} labels")

        # Note about filters
        print("\n   💡 Note: Gmail filters may still exist but won't apply without labels")
        print("      You can manually delete filters in Gmail settings if needed")

        return True

    except Exception as e:
        print(f"   ❌ Error during Gmail cleanup: {e}")
        return False

def show_current_status():
    """Show what's currently configured"""
    print("🔍 Current Gmail Automation Status")
    print("=" * 40)

    # Check for credentials
    cred_files = ['credentials.json', 'token.json']
    for cred_file in cred_files:
        if os.path.exists(cred_file):
            print(f"   ✅ {cred_file} - Found")
        else:
            print(f"   ❌ {cred_file} - Not found")

    # Check Gmail labels
    if GMAIL_CLEANUP_AVAILABLE and os.path.exists('credentials.json'):
        print("   🔍 Checking Gmail labels...")
        existing_labels = check_gmail_labels()
        if existing_labels is not None:
            if existing_labels:
                print(f"   🏷️  Gmail automation labels: {len(existing_labels)} found")
                for label_name in list(existing_labels.keys())[:3]:  # Show first 3
                    print(f"      • {label_name}")
                if len(existing_labels) > 3:
                    print(f"      ... and {len(existing_labels) - 3} more")
            else:
                print("   🏷️  Gmail automation labels: None found")
        else:
            print("   ⚠️  Could not check Gmail labels (authentication issue?)")

    # Check data files
    data_files = [
        'data/email_categories.json',
        'data/processing_state.json'
    ]
    for data_file in data_files:
        if os.path.exists(data_file):
            print(f"   📄 {data_file} - Exists")
        else:
            print(f"   📄 {data_file} - Not found")

    # Check models
    models_dir = Path('models')
    if models_dir.exists():
        model_files = list(models_dir.glob('*'))
        if model_files:
            print(f"   🤖 models/ - {len(model_files)} files found")
        else:
            print(f"   🤖 models/ - Empty directory")
    else:
        print(f"   🤖 models/ - Directory not found")

    # Check training data
    training_dirs = ['data/bootstrap', 'data/training', 'data/corrections']
    for training_dir in training_dirs:
        if os.path.exists(training_dir):
            files = list(Path(training_dir).glob('*'))
            print(f"   📊 {training_dir}/ - {len(files)} files")
        else:
            print(f"   📊 {training_dir}/ - Not found")

def reset_authentication():
    """Reset Gmail API authentication"""
    print("\n🔑 Resetting Authentication")
    print("=" * 30)

    token_files = ['token.json', 'token_*.json']
    removed_count = 0

    # Remove token files
    for pattern in token_files:
        if '*' in pattern:
            for token_file in Path('.').glob(pattern):
                try:
                    token_file.unlink()
                    print(f"   🗑️  Removed: {token_file}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Could not remove {token_file}: {e}")
        else:
            if os.path.exists(pattern):
                try:
                    os.remove(pattern)
                    print(f"   🗑️  Removed: {pattern}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Could not remove {pattern}: {e}")

    if removed_count == 0:
        print("   ✅ No authentication tokens found to remove")
    else:
        print(f"   ✅ Removed {removed_count} authentication files")

    # Check credentials
    if os.path.exists('credentials.json'):
        print("   📋 credentials.json preserved (needed for authentication)")
    else:
        print("   ⚠️  credentials.json not found - you'll need to download it from Google Cloud Console")

def reset_training_data():
    """Reset all training and correction data"""
    print("\n🧠 Resetting Training Data")
    print("=" * 30)

    # Directories to clean
    training_dirs = {
        'data/corrections': 'Semi-supervised learning corrections',
        'data/training': 'Exported training data files',
        'models': 'Trained ML models'
    }

    for dir_path, description in training_dirs.items():
        if os.path.exists(dir_path):
            try:
                # Count files before removal
                files = list(Path(dir_path).glob('*'))
                file_count = len([f for f in files if f.is_file()])

                if file_count > 0:
                    # Remove all files in directory
                    for file_path in files:
                        if file_path.is_file():
                            file_path.unlink()

                    print(f"   🗑️  Cleaned {dir_path}/ - Removed {file_count} files ({description})")
                else:
                    print(f"   ✅ {dir_path}/ - Already empty")

            except Exception as e:
                print(f"   ⚠️  Error cleaning {dir_path}: {e}")
        else:
            print(f"   📁 {dir_path}/ - Directory not found")

    # Keep bootstrap data (it's template data, not personal)
    print("   📦 data/bootstrap/ - Preserved (template training data)")

def reset_processing_state():
    """Reset processing state and session data"""
    print("\n📊 Resetting Processing State")
    print("=" * 35)

    state_files = [
        'data/processing_state.json',
        'processing_state.json'  # Legacy location
    ]

    removed_count = 0
    for state_file in state_files:
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
                print(f"   🗑️  Removed: {state_file}")
                removed_count += 1
            except Exception as e:
                print(f"   ⚠️  Could not remove {state_file}: {e}")

    if removed_count == 0:
        print("   ✅ No processing state files found")
    else:
        print(f"   ✅ Reset processing state ({removed_count} files removed)")

def create_fresh_setup_guide():
    """Create a step-by-step fresh setup guide"""
    print("\n🚀 Fresh Setup Guide")
    print("=" * 25)

    setup_steps = [
        "1. 🔑 AUTHENTICATION SETUP",
        "   • Make sure credentials.json is in the project root",
        "   • If missing, download from Google Cloud Console",
        "   • OAuth 2.0 credentials for Desktop application",
        "",
        "2. 📋 CHOOSE LABEL SYSTEM",
        "   • Consolidated (6 categories) - Recommended for most users",
        "   • Extended (10 categories) - For advanced granular control",
        "",
        "3. 🏷️ CREATE LABELS",
        "   python gmail_automation.py --labels-only --label-system consolidated",
        "   # OR",
        "   python gmail_automation.py --labels-only --label-system extended",
        "",
        "4. 🤖 BOOTSTRAP ML TRAINING",
        "   python gmail_automation.py --bootstrap-training",
        "",
        "5. 📧 START EMAIL SCANNING",
        "   # Small test scan first",
        "   python gmail_automation.py --scan-emails --max-emails 100 --days-back 7",
        "   ",
        "   # Full scan with high performance",
        "   python gmail_automation.py --scan-emails --concurrent --max-workers 8",
        "",
        "6. 🧠 IMPROVE WITH SEMI-SUPERVISED LEARNING",
        "   python gmail_automation.py --review-clusters",
        "",
        "7. 📈 MAINTENANCE (DAILY)",
        "   python gmail_automation.py --scan-unlabeled --days-back 1 --concurrent"
    ]

    for step in setup_steps:
        if step.startswith("   python"):
            print(f"   💻 {step.strip()}")
        elif step.startswith("   #"):
            print(f"   💬 {step.strip()}")
        else:
            print(step)

def show_reset_options():
    """Show different reset options"""
    print("\n🔧 Reset Options Available")
    print("=" * 30)

    options = {
        "1": "🏷️ Reset Gmail Labels Only (remove all automation labels)",
        "2": "🔑 Reset Authentication Only (keep training data & Gmail labels)",
        "3": "🧠 Reset Training Data Only (keep authentication & Gmail labels)",
        "4": "📊 Reset Processing State Only",
        "5": "🗑️  Complete Reset (Gmail labels + local files, keep credentials.json)",
        "6": "🔍 Show Current Status Only",
        "7": "❌ Cancel - No Reset"
    }

    for key, description in options.items():
        print(f"   {key}. {description}")

    return options

def perform_reset(option):
    """Perform the selected reset option"""
    print(f"\n⚡ Performing Reset Option {option}")
    print("=" * 40)

    if option == "1":
        # Gmail labels only
        if reset_gmail_labels_and_filters():
            print("\n✅ Gmail labels reset complete!")
        else:
            print("\n⚠️ Gmail labels reset failed or cancelled")

    elif option == "2":
        # Authentication only
        reset_authentication()
        print("\n✅ Authentication reset complete!")

    elif option == "3":
        # Training data only
        reset_training_data()
        print("\n✅ Training data reset complete!")

    elif option == "4":
        # Processing state only
        reset_processing_state()
        print("\n✅ Processing state reset complete!")

    elif option == "5":
        # Complete reset - Gmail first, then local files
        print("🗑️ Starting complete reset...")
        print("Step 1/4: Removing Gmail labels and filters")
        gmail_success = reset_gmail_labels_and_filters()

        print("\nStep 2/4: Resetting authentication")
        reset_authentication()

        print("\nStep 3/4: Resetting training data")
        reset_training_data()

        print("\nStep 4/4: Resetting processing state")
        reset_processing_state()

        print("\n✅ Complete reset finished!")
        if gmail_success:
            print("🏷️ Gmail labels removed successfully")
        else:
            print("⚠️ Gmail labels removal failed - you may need to remove manually")
        print("💡 You can now start fresh with the setup guide below")

    elif option == "6":
        print("✅ Status check complete!")

    elif option == "7":
        print("❌ Reset cancelled - no changes made")

def main():
    """Main function for reset tool"""
    print("🔄 Gmail Automation Suite - Reset and Fresh Start Tool")
    print("=" * 65)
    print("This tool helps you reset your Gmail automation setup and start fresh.\n")

    try:
        # Show current status
        show_current_status()

        # Show reset options
        options = show_reset_options()

        # Get user choice
        print(f"\n❓ Choose a reset option (1-7): ", end="")
        choice = input().strip()

        if choice not in options:
            print(f"❌ Invalid choice: {choice}")
            return 1

        # Confirm destructive operations
        if choice in ["1", "2", "3", "4", "5"]:
            print(f"\n⚠️  You selected: {options[choice]}")
            print("❓ Are you sure you want to proceed? This cannot be undone! (y/N): ", end="")
            confirm = input().strip().lower()

            if confirm != 'y' and confirm != 'yes':
                print("❌ Reset cancelled")
                return 0

        # Perform the reset
        perform_reset(choice)

        if choice == "1":
            print("\n🏷️ IMPORTANT: All automation labels removed from Gmail")

        if choice in ["2", "5"]:
            print("\n🔑 IMPORTANT: You'll need to re-authenticate when you run the automation next")

        if choice in ["3", "5"]:
            print("🧠 IMPORTANT: ML models will need to be retrained")

        if choice == "5":
            create_fresh_setup_guide()

        print(f"\n🎉 Reset operation completed successfully!")

    except KeyboardInterrupt:
        print(f"\n❌ Reset cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error during reset: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())