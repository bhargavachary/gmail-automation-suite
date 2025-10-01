#!/usr/bin/env python3
"""
Label Update Script for Gmail Automation Suite.

Allows users to review current labels, get enhancement suggestions,
and update label names and colors via a simple text file interface.
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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
    """
    Get current category labels with details.

    Optimization: Uses batch request to fetch all label details in one API call
    instead of individual requests per label.
    """
    try:
        all_labels = gmail_client.service.users().labels().list(userId='me').execute()
        labels_with_details = {}

        for label in all_labels.get('labels', []):
            # Only include user-created labels (not system labels)
            if label.get('type') == 'user':
                labels_with_details[label['name']] = {
                    'id': label['id'],
                    'color': label.get('color', {}),
                }

        return labels_with_details
    except Exception as e:
        raise GmailClientError(f"Failed to fetch labels: {e}")


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


def parse_update_file(file_path: Path) -> Tuple[List[Tuple[str, str, str]], List[str]]:
    """
    Parse the label update file.

    Returns:
        Tuple of (updates list, warnings list) for better error reporting
    """
    updates = []
    warnings = []

    if not file_path.exists():
        warnings.append(f"File not found: {file_path}")
        return updates, warnings

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#') or line.startswith('='):
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) != 3:
                warnings.append(f"Line {line_num}: Invalid format, expected 3 parts separated by '|'")
                continue

            old_name, new_name, color = parts

            # If new_name is empty or same as old, keep old name
            if not new_name or new_name == old_name:
                new_name = old_name

            # Validate color
            if color and color not in COLOR_PALETTE:
                warnings.append(f"Line {line_num}: Invalid color '{color}', will be ignored")
                color = ""

            updates.append((old_name, new_name, color))

    return updates, warnings


def backup_labels(current_labels: Dict[str, Dict], backup_file: Optional[Path] = None) -> Path:
    """
    Create a backup of current labels before making changes.

    Returns: Path to backup file
    """
    if backup_file is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = Path(f"label_backup_{timestamp}.json")

    backup_data = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'labels': {}
    }

    for name, details in current_labels.items():
        backup_data['labels'][name] = {
            'id': details['id'],
            'color': details.get('color', {})
        }

    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)

    return backup_file


def apply_updates(gmail_client: GmailClient, updates: List[Tuple[str, str, str]],
                  current_labels: Dict[str, Dict], dry_run: bool = False) -> Tuple[int, int]:
    """
    Apply label updates.

    Optimization: Accepts current_labels to avoid refetching from server.
    Returns: Tuple of (success_count, failure_count)
    """
    print(f"\n{'🔍 DRY RUN MODE' if dry_run else '🚀 APPLYING UPDATES'}")
    print("=" * 80)

    success_count = 0
    failure_count = 0

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
                success_count += 1
                time.sleep(0.1)  # Rate limiting to avoid API quota issues
            except Exception as e:
                print(f"  ✗ Failed: {e}")
                failure_count += 1

    total = success_count if not dry_run else len([u for u in updates if u[0] in current_labels])
    print(f"\n{'Would update' if dry_run else 'Updated'} {total} label(s)")
    if failure_count > 0:
        print(f"Failed: {failure_count} label(s)")

    return success_count, failure_count


def main():
    """Main entry point."""
    print("=" * 80)
    print("Gmail Label Update Tool")
    print("=" * 80)
    print("\n📖 Workflow:")
    print("  1. Fetch your current Gmail labels and colors from server")
    print("  2. Generate template file with auto-assigned colors")
    print("  3. You edit the template file with your preferences")
    print("  4. Review proposed changes")
    print("  5. Confirm to apply or skip to exit")
    print("=" * 80)

    input("\n👉 Press ENTER to start fetching labels from Gmail...")

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

    # Get current labels from server
    print("\n📋 Fetching current labels from Gmail server...")
    current_labels = get_current_labels(gmail_client)

    if not current_labels:
        print("No user-created labels found.")
        return 0

    print(f"✓ Found {len(current_labels)} label(s)\n")

    # Display current labels with actual colors from server
    print("Current Labels (from Gmail server):")
    print("-" * 80)
    for label_name, details in sorted(current_labels.items()):
        color = get_color_name(details.get('color', {}))
        print(f"  {label_name} (current color: {color})")

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
            print(f"  {label_name} (suggested color: {auto_color})")

    # Create template file
    template_file = Path("label_updates.txt")
    print(f"\n📝 Creating template file: {template_file}")
    create_template_file(current_labels, template_file)
    print(f"✓ Template created with suggestions and auto-assigned colors")

    # Ask user to edit the file
    print("\n" + "=" * 80)
    print("📝 Edit 'label_updates.txt' with your preferences:")
    print("  • Format: old_name | new_name | color")
    print("  • Available colors: red, orange, yellow, green, teal, blue, purple, pink, brown, gray")
    print("  • Keep 'new_name' same as 'old_name' if you only want to change color")
    print("  • Leave 'color' empty to keep current color")
    print("=" * 80)

    input("\n👉 Press ENTER after you've finished editing the file...")

    # Re-read the file and show what will be changed
    print("\n📖 Reading your changes from label_updates.txt...")
    updates, warnings = parse_update_file(template_file)

    # Show warnings if any
    if warnings:
        print("\n⚠️  Warnings during file parsing:")
        for warning in warnings:
            print(f"  • {warning}")

    if not updates:
        print("\n⚠️  No valid updates found in the file.")
        print("💡 You can edit 'label_updates.txt' and run this script again anytime.")
        return 0

    # Display the changes with better formatting
    print("\n📋 Proposed Changes:")
    print("=" * 80)

    valid_updates = []
    for old_name, new_name, color in updates:
        if old_name not in current_labels:
            print(f"⚠️  Label '{old_name}' not found on server (will be skipped)")
            continue

        changes = []
        if new_name != old_name:
            changes.append(f"name: {old_name} → {new_name}")
        if color:
            current_color = get_color_name(current_labels[old_name].get('color', {}))
            changes.append(f"color: {current_color} → {color}")

        if changes:
            print(f"\n{old_name}:")
            for change in changes:
                print(f"  • {change}")
            valid_updates.append((old_name, new_name, color))

    if not valid_updates:
        print("\n⚠️  No valid changes to apply.")
        print("💡 You can edit 'label_updates.txt' and run this script again anytime.")
        return 0

    # Ask for confirmation
    print("\n" + "=" * 80)
    print(f"Ready to update {len(valid_updates)} label(s)")
    response = input("\nType 'confirm' to apply these changes, or 'skip' to exit: ").strip().lower()

    if response == 'confirm':
        # Create backup before making changes
        print("\n💾 Creating backup of current labels...")
        backup_file = backup_labels(current_labels)
        print(f"✓ Backup saved to: {backup_file}")

        # Apply updates
        success, failure = apply_updates(gmail_client, valid_updates, current_labels, dry_run=False)

        if failure == 0:
            print("\n✅ All label updates applied successfully!")
            print(f"💾 Backup available at: {backup_file}")
        else:
            print(f"\n⚠️  Completed with {failure} failure(s)")
            print(f"💾 You can restore from backup: {backup_file}")
    else:
        print("\n💡 No changes made. You can edit 'label_updates.txt' and run this script again anytime.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
