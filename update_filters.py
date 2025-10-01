#!/usr/bin/env python3
"""
Filter Update Script for Gmail Automation Suite.

Fetch existing Gmail filters, display them, and update from rule-based
configuration file used in the classifier.

Usage:
    python update_filters.py [--help] [--read] [--update]

    --help      Show this help message
    --read      Read and display current filters from Gmail
    --update    Update filters from rule-based config (interactive)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gmail_automation.core.gmail_client import GmailClient, GmailClientError
from src.gmail_automation.core.config import Config, ConfigurationError


def format_filter_criteria(criteria: Dict) -> List[str]:
    """Format filter criteria into readable list."""
    parts = []

    if criteria.get('from'):
        parts.append(f"From: {criteria['from']}")
    if criteria.get('to'):
        parts.append(f"To: {criteria['to']}")
    if criteria.get('subject'):
        parts.append(f"Subject: {criteria['subject']}")
    if criteria.get('query'):
        parts.append(f"Query: {criteria['query']}")
    if criteria.get('negatedQuery'):
        parts.append(f"NOT: {criteria['negatedQuery']}")
    if criteria.get('hasAttachment'):
        parts.append("Has attachment")
    if criteria.get('excludeChats'):
        parts.append("Exclude chats")
    if criteria.get('size'):
        parts.append(f"Size: {criteria['size']}")
    if criteria.get('sizeComparison'):
        parts.append(f"Size comparison: {criteria['sizeComparison']}")

    return parts if parts else ["No criteria"]


def format_filter_actions(actions: Dict) -> List[str]:
    """Format filter actions into readable list."""
    parts = []

    if actions.get('addLabelIds'):
        parts.append(f"Add labels: {', '.join(actions['addLabelIds'])}")
    if actions.get('removeLabelIds'):
        parts.append(f"Remove labels: {', '.join(actions['removeLabelIds'])}")
    if actions.get('forward'):
        parts.append(f"Forward to: {actions['forward']}")
    if actions.get('markAsRead'):
        parts.append("Mark as read")
    if actions.get('markAsImportant'):
        parts.append("Mark as important")
    if actions.get('markAsSpam'):
        parts.append("Mark as spam")
    if actions.get('trash'):
        parts.append("Move to trash")

    return parts if parts else ["No actions"]


def export_filters_to_file(filters: List[Dict], output_file: Path, labels: Dict[str, str]):
    """
    Export filters to a text file in human-readable format.

    Args:
        filters: List of filter objects from Gmail API
        output_file: Path to output file
        labels: Dict mapping label IDs to names
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Gmail Filters Export\n")
        f.write("# This file shows all current Gmail filters\n")
        f.write("# Format: Each filter shows ID, criteria, and actions\n")
        f.write("#\n")
        f.write(f"# Total Filters: {len(filters)}\n")
        f.write("# Generated: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write("\n" + "=" * 80 + "\n\n")

        for idx, filter_obj in enumerate(filters, 1):
            filter_id = filter_obj.get('id', 'unknown')
            criteria = filter_obj.get('criteria', {})
            actions = filter_obj.get('action', {})

            f.write(f"Filter #{idx}\n")
            f.write("-" * 80 + "\n")
            f.write(f"ID: {filter_id}\n\n")

            f.write("Criteria:\n")
            for criterion in format_filter_criteria(criteria):
                f.write(f"  • {criterion}\n")
            f.write("\n")

            f.write("Actions:\n")
            for action in format_filter_actions(actions):
                # Replace label IDs with names
                action_text = action
                if 'labels:' in action or 'Add labels:' in action or 'Remove labels:' in action:
                    for label_id, label_name in labels.items():
                        action_text = action_text.replace(label_id, label_name)
                f.write(f"  • {action_text}\n")
            f.write("\n" + "=" * 80 + "\n\n")


def analyze_filter_differences(filters: List[Dict], config: Config, labels: Dict[str, str]) -> Dict:
    """
    Analyze differences between Gmail filters and config rules.

    Returns dict with:
        - filters_by_category: filters grouped by category
        - config_domains_by_category: domains from config
        - missing_in_gmail: domains in config but no filter
        - extra_in_gmail: filters not matching config
    """
    analysis = {
        'filters_by_category': {},
        'config_domains_by_category': {},
        'missing_in_gmail': {},
        'extra_in_gmail': [],
        'total_filters': len(filters),
        'total_config_rules': 0
    }

    # Group filters by category (based on label action)
    for filter_obj in filters:
        actions = filter_obj.get('action', {})
        criteria = filter_obj.get('criteria', {})

        # Get label from actions
        label_ids = actions.get('addLabelIds', [])
        if label_ids:
            for label_id in label_ids:
                label_name = labels.get(label_id, 'Unknown')
                if label_name not in analysis['filters_by_category']:
                    analysis['filters_by_category'][label_name] = []
                analysis['filters_by_category'][label_name].append(criteria)

    # Get domains from config
    for category_name, category_config in config.categories.items():
        domains = category_config.domains
        all_domains = []
        all_domains.extend(domains.get('high_confidence', []))
        all_domains.extend(domains.get('medium_confidence', []))

        analysis['config_domains_by_category'][category_name] = all_domains
        analysis['total_config_rules'] += len(all_domains)

        # Find missing domains (in config but not in Gmail)
        existing_domains = set()
        for filter_criteria in analysis['filters_by_category'].get(category_name, []):
            from_field = filter_criteria.get('from', '')
            if from_field:
                existing_domains.add(from_field)

        missing = set(all_domains) - existing_domains
        if missing:
            analysis['missing_in_gmail'][category_name] = sorted(list(missing))

    return analysis


def read_filters_command():
    """Read and display current filters from Gmail."""
    print("=" * 80)
    print("Gmail Filters - Current State")
    print("=" * 80)

    # Initialize Gmail client
    config_dir = Path("data")
    try:
        print("\n🔌 Connecting to Gmail...")
        gmail_client = GmailClient(
            credentials_file="credentials.json",
            token_file="token.json",
            config_dir=config_dir
        )
    except GmailClientError as e:
        print(f"❌ Error: {e}")
        return 1

    # Get current filters
    print("📋 Fetching filters from Gmail server...")
    try:
        filters = gmail_client.get_filters()
        labels_dict = gmail_client.get_labels()
        # Reverse mapping for label IDs to names
        label_id_to_name = {v: k for k, v in labels_dict.items()}
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    if not filters:
        print("\n⚠️  No filters found.")
        return 0

    print(f"\n✓ Found {len(filters)} filter(s)\n")

    # Display filters
    print("Current Filters:")
    print("-" * 80)

    for idx, filter_obj in enumerate(filters, 1):
        filter_id = filter_obj.get('id', 'unknown')
        criteria = filter_obj.get('criteria', {})
        actions = filter_obj.get('action', {})

        print(f"\n{idx:2d}. Filter ID: {filter_id}")
        print("    Criteria:")
        for criterion in format_filter_criteria(criteria):
            print(f"      • {criterion}")
        print("    Actions:")
        for action in format_filter_actions(actions):
            # Replace label IDs with names
            action_text = action
            for label_id, label_name in label_id_to_name.items():
                action_text = action_text.replace(label_id, label_name)
            print(f"      • {action_text}")

    print("\n" + "-" * 80)
    print(f"\nTotal: {len(filters)} filter(s)")

    # Load config and compare
    print("\n" + "=" * 80)
    print("📊 Comparing with Configuration Rules")
    print("=" * 80)

    try:
        print("\n📖 Loading configuration from data/...")
        config = Config(config_dir=config_dir)
        print(f"✓ Loaded {len(config.categories)} categories from config")

        # Analyze differences
        analysis = analyze_filter_differences(filters, config, label_id_to_name)

        print("\n📋 Analysis Results:")
        print("-" * 80)
        print(f"Total Gmail filters: {analysis['total_filters']}")
        print(f"Total config rules: {analysis['total_config_rules']}")

        # Show breakdown by category
        print("\n📁 Breakdown by Category:")
        for category_name in sorted(config.categories.keys()):
            gmail_count = len(analysis['filters_by_category'].get(category_name, []))
            config_count = len(analysis['config_domains_by_category'].get(category_name, []))

            status = "✓" if gmail_count == config_count else "⚠️"
            print(f"\n  {status} {category_name}:")
            print(f"      Gmail filters: {gmail_count}")
            print(f"      Config rules: {config_count}")

            # Show missing domains
            if category_name in analysis['missing_in_gmail']:
                missing = analysis['missing_in_gmail'][category_name]
                print(f"      Missing in Gmail: {len(missing)} domain(s)")
                if len(missing) <= 3:
                    for domain in missing:
                        print(f"        - {domain}")
                else:
                    for domain in missing[:3]:
                        print(f"        - {domain}")
                    print(f"        ... and {len(missing) - 3} more")

        # Summary
        total_missing = sum(len(v) for v in analysis['missing_in_gmail'].values())
        if total_missing > 0:
            print("\n" + "=" * 80)
            print(f"⚠️  Summary: {total_missing} rule(s) from config are missing in Gmail")
            print("💡 Run with --update to sync configuration to Gmail")
        else:
            print("\n" + "=" * 80)
            print("✅ All config rules are present in Gmail!")

    except ConfigurationError as e:
        print(f"\n⚠️  Could not load config: {e}")
        print("💡 Comparison skipped")

    # Ask to export
    response = input("\n💾 Export to file? (yes/no): ").strip().lower()
    if response == 'yes':
        output_file = Path("gmail_filters_export.txt")
        export_filters_to_file(filters, output_file, label_id_to_name)
        print(f"✓ Exported to {output_file}")

    return 0


def create_filters_from_config(gmail_client: GmailClient, config: Config,
                                dry_run: bool = False) -> Tuple[int, int]:
    """
    Create filters from configuration file.

    Returns:
        Tuple of (success_count, failure_count)
    """
    print(f"\n{'🔍 DRY RUN MODE' if dry_run else '🚀 CREATING FILTERS'}")
    print("=" * 80)

    success_count = 0
    failure_count = 0

    # Get or create labels
    labels = gmail_client.get_labels()

    for category_name, category_config in config.categories.items():
        print(f"\n📁 Category: {category_name}")

        # Ensure label exists
        if category_name not in labels:
            if dry_run:
                print(f"  Would create label: {category_name}")
            else:
                try:
                    label_id = gmail_client.create_label(category_name)
                    labels[category_name] = label_id
                    print(f"  ✓ Created label: {category_name}")
                except Exception as e:
                    print(f"  ✗ Failed to create label: {e}")
                    failure_count += 1
                    continue

        label_id = labels.get(category_name)

        # Create filters from domains
        domains = category_config.domains
        high_domains = domains.get('high_confidence', [])
        medium_domains = domains.get('medium_confidence', [])

        print(f"  High confidence domains: {len(high_domains)}")
        print(f"  Medium confidence domains: {len(medium_domains)}")

        if dry_run:
            print(f"  Would create {len(high_domains) + len(medium_domains)} domain-based filters")
        else:
            # Create filters
            try:
                created_filters = gmail_client.create_category_filters(
                    category_name, category_config, label_id
                )
                success_count += len(created_filters)
                print(f"  ✓ Created {len(created_filters)} filters")
                time.sleep(0.2)  # Rate limiting
            except Exception as e:
                print(f"  ✗ Failed to create filters: {e}")
                failure_count += 1

    print(f"\n{'Would create' if dry_run else 'Created'} {success_count} filter(s)")
    if failure_count > 0:
        print(f"Failed: {failure_count} operation(s)")

    return success_count, failure_count


def update_filters_interactive():
    """Interactive step-by-step filter update workflow."""
    print("=" * 80)
    print("Gmail Filter Update Tool - Interactive Mode")
    print("=" * 80)

    # Step 1: Explain workflow
    print("\n📖 This tool will guide you through 5 steps:")
    print("  Step 1: Fetch current filters from Gmail")
    print("  Step 2: Export filters to readable text file")
    print("  Step 3: Load rule-based configuration")
    print("  Step 4: Preview filters to be created")
    print("  Step 5: Apply changes with backup")
    print("=" * 80)

    response = input("\n👉 Ready to start? (yes/no): ").strip().lower()
    if response != 'yes':
        print("💡 Exited. Run again when ready.")
        return 0

    # STEP 1: Fetch current filters
    print("\n" + "=" * 80)
    print("STEP 1: Fetching Current Filters from Gmail")
    print("=" * 80)

    response = input("\n👉 Press ENTER to fetch filters (or 'skip' to use cached data): ").strip().lower()

    # Initialize Gmail client
    config_dir = Path("data")
    try:
        print("\n🔌 Connecting to Gmail...")
        gmail_client = GmailClient(
            credentials_file="credentials.json",
            token_file="token.json",
            config_dir=config_dir
        )
    except GmailClientError as e:
        print(f"❌ Error: {e}")
        return 1

    if response != 'skip':
        print("📋 Fetching filters from server...")
        try:
            current_filters = gmail_client.get_filters()
            labels_dict = gmail_client.get_labels()
            label_id_to_name = {v: k for k, v in labels_dict.items()}
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1

        print(f"✓ Found {len(current_filters)} filter(s)")

        # Show summary
        print("\nFilter Summary:")
        print("-" * 80)
        for idx, filter_obj in enumerate(current_filters[:5], 1):
            criteria = filter_obj.get('criteria', {})
            criterion_text = format_filter_criteria(criteria)[0]
            print(f"  {idx}. {criterion_text}")
        if len(current_filters) > 5:
            print(f"  ... and {len(current_filters) - 5} more")
        print("-" * 80)
    else:
        print("⏭️  Skipped fetching.")
        try:
            current_filters = gmail_client.get_filters()
            labels_dict = gmail_client.get_labels()
            label_id_to_name = {v: k for k, v in labels_dict.items()}
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1

    # STEP 2: Export to file
    print("\n" + "=" * 80)
    print("STEP 2: Export Filters to File")
    print("=" * 80)

    response = input("\n👉 Press ENTER to export (or 'skip' to continue): ").strip().lower()

    export_file = Path("gmail_filters_export.txt")

    if response != 'skip':
        print(f"\n💾 Exporting to {export_file}...")
        export_filters_to_file(current_filters, export_file, label_id_to_name)
        print(f"✓ Exported {len(current_filters)} filters")
        print(f"📄 Review the file to see all current filters")
    else:
        print("⏭️  Skipped export.")

    # STEP 3: Load configuration
    print("\n" + "=" * 80)
    print("STEP 3: Load Rule-Based Configuration")
    print("=" * 80)

    response = input("\n👉 Press ENTER to load config (or 'skip' to continue): ").strip().lower()

    try:
        print("\n📖 Loading configuration from data/...")
        config = Config(config_dir=config_dir)
        print(f"✓ Loaded configuration")
        print(f"  Categories: {len(config.categories)}")
        print(f"  Category names: {', '.join(list(config.categories.keys())[:5])}")
        if len(config.categories) > 5:
            print(f"  ... and {len(config.categories) - 5} more")
    except ConfigurationError as e:
        print(f"❌ Error loading config: {e}")
        return 1

    # STEP 4: Preview filters
    print("\n" + "=" * 80)
    print("STEP 4: Preview Filters to Create")
    print("=" * 80)

    response = input("\n👉 Press ENTER to preview (or 'skip' to final step): ").strip().lower()

    if response != 'skip':
        print("\n📋 Preview of filters to be created:")
        print("-" * 80)

        total_filters = 0
        for category_name, category_config in list(config.categories.items())[:3]:
            domains = category_config.domains
            high_count = len(domains.get('high_confidence', []))
            medium_count = len(domains.get('medium_confidence', []))
            total = high_count + medium_count
            total_filters += total

            print(f"\n{category_name}:")
            print(f"  • High confidence domains: {high_count}")
            print(f"  • Medium confidence domains: {medium_count}")
            print(f"  • Total filters: {total}")

        if len(config.categories) > 3:
            remaining = len(config.categories) - 3
            print(f"\n... and {remaining} more categories")

        print(f"\n{'=' * 80}")
        print(f"Estimated total filters to create: {total_filters}+")
    else:
        print("⏭️  Skipped preview.")

    # STEP 5: Apply changes
    print("\n" + "=" * 80)
    print("STEP 5: Create Filters from Configuration")
    print("=" * 80)
    print("\n⚠️  Warning: This will create new filters based on your configuration.")
    print("💡 Tip: Existing filters will not be modified or deleted.")

    response = input("\n👉 Type 'confirm' to create filters, or 'skip' to exit: ").strip().lower()

    if response == 'confirm' or response == 'yes':
        # Backup current filters
        print("\n💾 Creating backup of current filters...")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = Path(f"filters_backup_{timestamp}.json")

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'filters': current_filters
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Backup saved to: {backup_file}")

        # Create filters
        success, failure = create_filters_from_config(gmail_client, config, dry_run=False)

        if failure == 0:
            print("\n✅ All filters created successfully!")
            print(f"💾 Backup available at: {backup_file}")
        else:
            print(f"\n⚠️  Completed with {failure} failure(s)")
            print(f"💾 You can review backup: {backup_file}")
    else:
        print("\n💡 No changes made. Your existing filters remain unchanged.")

    return 0


def show_help():
    """Display help information."""
    print("=" * 80)
    print("Gmail Filter Update Tool - Help")
    print("=" * 80)
    print("\n📖 Usage:")
    print("  python update_filters.py [--help] [--read] [--update]")
    print("\n📋 Commands:")
    print("  --help      Show this help message and exit")
    print("  --read      Read and display current filters from Gmail")
    print("  --update    Create filters from rule-based config (interactive)")
    print("\n🔄 Workflow:")
    print("  1. Run with --read to view current filters")
    print("  2. Run with --update to create new filters from config")
    print("  3. Config is loaded from data/gmail_rules.yaml")
    print("  4. Filters are created for each category's domains")
    print("  5. Automatic backup before creating filters")
    print("\n💡 Features:")
    print("  • Export current filters to readable text file")
    print("  • Create filters from rule-based configuration")
    print("  • Preview filters before creating")
    print("  • Automatic backup of existing filters")
    print("  • Does not modify or delete existing filters")
    print("=" * 80)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Gmail Filter Update Tool - Manage Gmail filters from config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update_filters.py --help          Show help information
  python update_filters.py --read          Read current filters from Gmail
  python update_filters.py --update        Create filters from config (interactive)

Features:
  • Export current filters to readable text file
  • Create filters from rule-based configuration
  • Preview before creating
  • Automatic backup
        """
    )

    parser.add_argument(
        '--read',
        action='store_true',
        help='Read and display current filters from Gmail server'
    )

    parser.add_argument(
        '--update',
        action='store_true',
        help='Create filters from config (interactive workflow)'
    )

    args = parser.parse_args()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n💡 Tip: Use --read to view current filters or --update to create from config")
        return 0

    # Execute command based on arguments
    try:
        if args.read:
            return read_filters_command()
        elif args.update:
            return update_filters_interactive()
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting safely...")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
