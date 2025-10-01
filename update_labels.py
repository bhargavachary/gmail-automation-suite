#!/usr/bin/env python3
"""
Label Update Script for Gmail Automation Suite.

Allows users to review current labels, get enhancement suggestions,
and update label names and colors via a simple text file interface.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gmail_automation.core.gmail_client import GmailClient, GmailClientError
from src.gmail_automation.core.config import Config


# Enhanced color palette with Gmail-supported colors
COLOR_PALETTE = {
    "red": {"textColor": "#ffffff", "backgroundColor": "#db4437"},
    "orange": {"textColor": "#ffffff", "backgroundColor": "#f4b400"},
    "yellow": {"textColor": "#000000", "backgroundColor": "#fbbc04"},
    "green": {"textColor": "#ffffff", "backgroundColor": "#0f9d58"},
    "teal": {"textColor": "#ffffff", "backgroundColor": "#00bcd4"},
    "blue": {"textColor": "#ffffff", "backgroundColor": "#4285f4"},
    "purple": {"textColor": "#ffffff", "backgroundColor": "#ab47bc"},
    "pink": {"textColor": "#ffffff", "backgroundColor": "#e91e63"},
    "brown": {"textColor": "#ffffff", "backgroundColor": "#795548"},
    "gray": {"textColor": "#ffffff", "backgroundColor": "#9e9e9e"},
}

# Color rotation order for automatic assignment
COLOR_ROTATION = ["blue", "green", "orange", "purple", "red", "teal", "pink", "yellow", "brown", "gray"]

# Suggested category enhancements
CATEGORY_SUGGESTIONS = {
    "Finance & Bills": {"emoji": "💰", "color": "green"},
    "Work & Professional": {"emoji": "💼", "color": "blue"},
    "Shopping & E-commerce": {"emoji": "🛒", "color": "orange"},
    "Travel & Transportation": {"emoji": "✈️", "color": "teal"},
    "Social & Community": {"emoji": "👥", "color": "purple"},
    "Entertainment & Media": {"emoji": "🎬", "color": "pink"},
    "Health & Wellness": {"emoji": "🏥", "color": "red"},
    "Education & Learning": {"emoji": "📚", "color": "blue"},
    "Technology & Software": {"emoji": "💻", "color": "gray"},
    "News & Updates": {"emoji": "📰", "color": "brown"},
}


def get_current_labels(gmail_client: GmailClient) -> Dict[str, Dict]:
    """Get current category labels with details."""
    all_labels = gmail_client.service.users().labels().list(userId='me').execute()
    labels_with_details = {}

    for label in all_labels.get('labels', []):
        label_id = label['id']
        # Only include user-created labels (not system labels)
        if label.get('type') == 'user':
            label_details = gmail_client.service.users().labels().get(
                userId='me', id=label_id
            ).execute()
            labels_with_details[label['name']] = {
                'id': label_id,
                'color': label_details.get('color', {}),
            }

    return labels_with_details


def suggest_enhancements(current_name: str) -> Dict[str, str]:
    """Suggest enhancements for a label name."""
    # Try exact match first
    for category, suggestion in CATEGORY_SUGGESTIONS.items():
        if current_name.lower() in category.lower() or category.lower() in current_name.lower():
            return {
                "suggested_name": f"{suggestion['emoji']} {category}",
                "suggested_color": suggestion['color']
            }

    # Default suggestion - just add emoji if not present
    has_emoji = any(char for char in current_name if ord(char) > 127)
    if not has_emoji:
        return {
            "suggested_name": f"📁 {current_name}",
            "suggested_color": "blue"
        }

    return {
        "suggested_name": current_name,
        "suggested_color": "blue"
    }


def create_template_file(current_labels: Dict[str, Dict], output_file: Path):
    """Create a template file with current labels and suggestions."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Gmail Label Update Configuration\n")
        f.write("# Format: old_name | new_name | color\n")
        f.write("# Available colors: red, orange, yellow, green, teal, blue, purple, pink, brown, gray\n")
        f.write("# Lines starting with # are ignored\n")
        f.write("# Leave 'new_name' empty (or same as old) to keep current name\n")
        f.write("# Leave 'color' empty to keep current color\n\n")

        f.write("=" * 80 + "\n\n")

        sorted_labels = sorted(current_labels.items())
        for idx, (label_name, details) in enumerate(sorted_labels):
            suggestion = suggest_enhancements(label_name)
            current_color = get_color_name(details.get('color', {}))

            # Assign different color from rotation for each label
            suggested_color = COLOR_ROTATION[idx % len(COLOR_ROTATION)]

            f.write(f"# Current: {label_name}\n")
            f.write(f"# Suggested: {suggestion['suggested_name']} (color: {suggested_color})\n")
            f.write(f"{label_name} | {suggestion['suggested_name']} | {suggested_color}\n\n")


def get_color_name(color_config: Dict) -> str:
    """Get color name from color configuration."""
    if not color_config:
        return "default"

    bg = color_config.get('backgroundColor', '').lower()
    for name, config in COLOR_PALETTE.items():
        if config['backgroundColor'].lower() == bg:
            return name
    return "custom"


def parse_update_file(file_path: Path) -> List[Tuple[str, str, str]]:
    """Parse the label update file."""
    updates = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#') or line.startswith('='):
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) != 3:
                print(f"⚠️  Warning: Invalid format on line {line_num}, skipping: {line}")
                continue

            old_name, new_name, color = parts

            # If new_name is empty or same as old, keep old name
            if not new_name or new_name == old_name:
                new_name = old_name

            # Validate color
            if color and color not in COLOR_PALETTE:
                print(f"⚠️  Warning: Invalid color '{color}' on line {line_num}, using default")
                color = ""

            updates.append((old_name, new_name, color))

    return updates


def apply_updates(gmail_client: GmailClient, updates: List[Tuple[str, str, str]], dry_run: bool = False):
    """Apply label updates."""
    current_labels = get_current_labels(gmail_client)

    print(f"\n{'🔍 DRY RUN MODE' if dry_run else '🚀 APPLYING UPDATES'}")
    print("=" * 80)

    updated_count = 0

    for old_name, new_name, color in updates:
        if old_name not in current_labels:
            print(f"⚠️  Label not found: {old_name}, skipping...")
            continue

        label_id = current_labels[old_name]['id']
        changes = []

        # Build update payload
        update_body = {}

        if new_name != old_name:
            update_body['name'] = new_name
            changes.append(f"name: {old_name} → {new_name}")

        if color and color in COLOR_PALETTE:
            update_body['color'] = COLOR_PALETTE[color]
            changes.append(f"color: {color}")

        if not changes:
            continue

        print(f"\n{'Would update' if dry_run else 'Updating'}: {old_name}")
        for change in changes:
            print(f"  - {change}")

        if not dry_run:
            try:
                gmail_client.service.users().labels().update(
                    userId='me',
                    id=label_id,
                    body=update_body
                ).execute()
                print(f"  ✓ Success")
                updated_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {e}")

    print(f"\n{'Would update' if dry_run else 'Updated'} {updated_count} label(s)")


def main():
    """Main entry point."""
    print("=" * 80)
    print("Gmail Label Update Tool")
    print("=" * 80)

    # Initialize Gmail client
    config_dir = Path("data")
    try:
        gmail_client = GmailClient(
            credentials_file="credentials.json",
            token_file="token.json",
            config_dir=config_dir
        )
    except GmailClientError as e:
        print(f"❌ Error: {e}")
        return 1

    # Get current labels
    print("\n📋 Fetching current labels...")
    current_labels = get_current_labels(gmail_client)

    if not current_labels:
        print("No user-created labels found.")
        return 0

    print(f"Found {len(current_labels)} label(s)\n")

    # Display current labels
    print("Current Labels:")
    print("-" * 80)
    for label_name, details in sorted(current_labels.items()):
        color = get_color_name(details.get('color', {}))
        print(f"  {label_name} (color: {color})")

    # Show suggestions with auto-assigned colors
    print("\n💡 Suggested Enhancements (each label gets a different color):")
    print("-" * 80)
    sorted_labels = sorted(current_labels.keys())
    for idx, label_name in enumerate(sorted_labels):
        suggestion = suggest_enhancements(label_name)
        auto_color = COLOR_ROTATION[idx % len(COLOR_ROTATION)]
        if suggestion['suggested_name'] != label_name:
            print(f"  {label_name}")
            print(f"    → {suggestion['suggested_name']} (color: {auto_color})")
        else:
            print(f"  {label_name} (color: {auto_color})")

    # Create template file
    template_file = Path("label_updates.txt")
    print(f"\n📝 Creating template file: {template_file}")
    create_template_file(current_labels, template_file)
    print(f"✓ Template created with suggestions")

    # Ask user to edit the file
    print("\n" + "=" * 80)
    print("Next Steps:")
    print("1. Edit 'label_updates.txt' with your desired changes")
    print("2. Save the file and return here")
    print("=" * 80)

    input("\n📝 Press ENTER when you've finished editing the file...")

    # Re-read the file and show what will be changed
    print("\n📖 Reading your changes from label_updates.txt...")
    updates = parse_update_file(template_file)

    if not updates:
        print("\n⚠️  No updates found in the file.")
        print("💡 You can edit 'label_updates.txt' and run this script again anytime.")
        return 0

    # Display the changes
    print("\n📋 Proposed Changes:")
    print("=" * 80)

    for old_name, new_name, color in updates:
        if old_name not in current_labels:
            print(f"⚠️  Label not found: {old_name} (will be skipped)")
            continue

        changes = []
        if new_name != old_name:
            changes.append(f"name: {old_name} → {new_name}")
        if color:
            changes.append(f"color: {color}")

        if changes:
            print(f"\n{old_name}:")
            for change in changes:
                print(f"  • {change}")

    # Ask for confirmation
    print("\n" + "=" * 80)
    response = input("\nType 'confirm' to apply these changes, or 'skip' to exit: ").strip().lower()

    if response == 'confirm':
        apply_updates(gmail_client, updates, dry_run=False)
        print("\n✅ Label updates applied successfully!")
    else:
        print("\n💡 No changes made. You can edit 'label_updates.txt' and run this script again anytime.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
