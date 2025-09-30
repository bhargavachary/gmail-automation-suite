"""
Command-line interface for Gmail Automation Suite.

Provides a user-friendly CLI for email classification, label management,
and batch operations with comprehensive configuration options.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .core.gmail_client import GmailClient, GmailClientError
from .core.classifier import EmailClassifier, EmailClassifierError
from .core.config import Config, ConfigurationError
from .utils.migration import LegacyMigrator
from .utils.logger import get_logger, setup_root_logger

logger = get_logger(__name__)


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup and configure command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="gmail-automation",
        description="Gmail Automation Suite - Intelligent email management and classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gmail-automation classify --max-emails 100 --method hybrid --apply-labels
  gmail-automation classify --max-emails 0 --method hybrid --apply-labels  # Exhaustive search
  gmail-automation labels --create "Work Projects" --color blue
  gmail-automation filters --create "🏦 Finance & Bills"
  gmail-automation --dry-run filters --create-all
  gmail-automation --dry-run reset --all
  gmail-automation reset --filters --confirm --backup-to backup.json
  gmail-automation migrate --legacy-file gmail_automation.py --output-dir data
  gmail-automation config --validate --config-dir data
        """
    )

    # Global options
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("data"),
        help="Configuration directory (default: data)"
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default="credentials.json",
        help="Gmail API credentials file (default: credentials.json)"
    )
    parser.add_argument(
        "--token",
        type=str,
        default="token.json",
        help="OAuth token file (default: token.json)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Classification command
    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify emails using configured rules"
    )
    classify_parser.add_argument(
        "--method",
        choices=["rule_based", "llm", "ml", "random_forest", "hybrid"],
        default="rule_based",
        help="Classification method (default: rule_based)"
    )
    classify_parser.add_argument(
        "--max-emails",
        type=int,
        default=100,
        help="Maximum number of emails to process (default: 100, use 0 for exhaustive search)"
    )
    classify_parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Gmail search query (default: 'is:unread' for small batches, '' for large batches)"
    )
    classify_parser.add_argument(
        "--apply-labels",
        action="store_true",
        help="Apply labels to classified emails"
    )
    classify_parser.add_argument(
        "--report",
        type=Path,
        help="Save classification report to file"
    )
    classify_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (force reprocessing of all emails)"
    )
    classify_parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics before processing"
    )
    classify_parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads to use for parallel processing (default: 4, reduced for API stability)"
    )

    # Label management command
    labels_parser = subparsers.add_parser(
        "labels",
        help="Manage Gmail labels"
    )
    labels_parser.add_argument(
        "--list",
        action="store_true",
        help="List all existing labels"
    )
    labels_parser.add_argument(
        "--create",
        type=str,
        help="Create a new label"
    )
    labels_parser.add_argument(
        "--color",
        type=str,
        help="Color for new label (e.g., red, blue, green)"
    )
    labels_parser.add_argument(
        "--delete",
        type=str,
        help="Delete a label by name"
    )

    # Migration command
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate from legacy Gmail automation code"
    )
    migrate_parser.add_argument(
        "--legacy-file",
        type=Path,
        required=True,
        help="Path to legacy gmail_automation.py file"
    )
    migrate_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for migrated configuration (default: data)"
    )
    migrate_parser.add_argument(
        "--report",
        type=Path,
        help="Save migration report to file"
    )

    # Configuration command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management and validation"
    )
    config_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate current configuration"
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--export",
        type=Path,
        help="Export configuration to file"
    )

    # Filter management command
    filters_parser = subparsers.add_parser(
        "filters",
        help="Manage Gmail filters for automatic email processing"
    )
    filters_parser.add_argument(
        "--list",
        action="store_true",
        help="List all existing Gmail filters"
    )
    filters_parser.add_argument(
        "--create",
        type=str,
        help="Create filters for a specific category (e.g., 'Finance & Bills')"
    )
    filters_parser.add_argument(
        "--create-all",
        action="store_true",
        help="Create filters for all configured categories"
    )
    filters_parser.add_argument(
        "--delete",
        type=str,
        help="Delete a specific filter by ID"
    )
    filters_parser.add_argument(
        "--summary",
        action="store_true",
        help="Show detailed summary of all filters"
    )
    filters_parser.add_argument(
        "--report",
        type=Path,
        help="Save filter report to file"
    )

    # Cache management command
    cache_parser = subparsers.add_parser(
        "cache",
        help="Manage email classification cache"
    )
    cache_parser.add_argument(
        "--stats",
        action="store_true",
        help="Show cache statistics"
    )
    cache_parser.add_argument(
        "--apply-labels",
        action="store_true",
        help="Apply labels to all cached classified emails"
    )
    cache_parser.add_argument(
        "--export",
        type=Path,
        help="Export cached classifications to JSON file"
    )
    cache_parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="Remove cache entries older than DAYS (only labeled emails)"
    )

    # Reset command
    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset Gmail automation components (labels, filters, or all)"
    )
    reset_parser.add_argument(
        "--all",
        action="store_true",
        help="Reset all labels and filters"
    )
    reset_parser.add_argument(
        "--labels",
        action="store_true",
        help="Reset only category labels"
    )
    reset_parser.add_argument(
        "--filters",
        action="store_true",
        help="Reset only Gmail filters"
    )
    reset_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm destructive operations (required for actual reset)"
    )
    reset_parser.add_argument(
        "--backup-to",
        type=Path,
        help="Save backup before reset"
    )
    reset_parser.add_argument(
        "--category-pattern",
        type=str,
        help="Pattern for label matching (supports glob: Test*, *temp*, exact names). Default: smart category detection"
    )

    return parser


def handle_classify_command(args) -> int:
    """Handle email classification command."""
    try:
        # Load configuration
        config = Config(config_dir=args.config_dir)

        # Initialize Gmail client
        gmail_client = GmailClient(
            credentials_file=args.credentials,
            token_file=args.token,
            config_dir=args.config_dir
        )

        # Initialize classifier with ML models and cache
        model_dir = args.config_dir / "backups" / "20250928"
        cache_dir = args.config_dir / "cache"
        classifier = EmailClassifier(
            config,
            str(model_dir) if model_dir.exists() else None,
            cache_dir
        )

        # Determine intelligent query based on max_emails and user input
        if args.query is None:
            # For large batches (1000+) or exhaustive search (0), search all emails; for small batches, use unread
            query = "" if (args.max_emails >= 1000 or args.max_emails == 0) else "is:unread"
        else:
            query = args.query

        # Handle exhaustive search (max_emails = 0)
        max_results = None if args.max_emails == 0 else args.max_emails
        search_mode = "exhaustive" if args.max_emails == 0 else f"up to {args.max_emails} emails"

        print(f"Searching for emails with query: '{query}' ({search_mode})")
        message_ids = gmail_client.search_messages(query, max_results)

        if not message_ids:
            print("No emails found matching the query.")
            return 0

        # Show cache statistics if requested
        if hasattr(args, 'cache_stats') and args.cache_stats:
            cache_stats = classifier.cache.get_classification_stats()
            print(f"\n📊 Cache Statistics:")
            print(f"  Total processed emails: {cache_stats.get('total_processed', 0)}")
            print(f"  Total classified emails: {cache_stats.get('total_classified', 0)}")
            print(f"  Total labeled emails: {cache_stats.get('total_labeled', 0)}")
            print(f"  Pending labels: {cache_stats.get('pending_labels', 0)}")
            print(f"  Classification rate: {cache_stats.get('classification_rate', 0):.1%}")
            print(f"  Labeling rate: {cache_stats.get('labeling_rate', 0):.1%}")

        print(f"Found {len(message_ids)} emails. Starting classification...")

        # Use efficient cache-first classification that only fetches uncached emails
        use_cache = not (hasattr(args, 'no_cache') and args.no_cache)
        apply_labels = args.apply_labels and not args.dry_run
        results = classifier.classify_batch_from_message_ids(
            gmail_client,
            message_ids,
            method=args.method,
            use_cache=use_cache,
            apply_labels=apply_labels,
            batch_size=100
        )

        # Generate statistics
        stats = classifier.get_classification_stats(results)

        # Display results
        print(f"\nClassification Results:")
        print(f"  Total emails: {stats['total_emails']}")
        print(f"  Classified: {stats['classified_emails']}")
        print(f"  Classification rate: {stats['classification_rate']:.1%}")
        print(f"  Average confidence: {stats['average_confidence']:.2f}")

        if stats['category_distribution']:
            print(f"\nCategory Distribution:")
            for category, count in stats['category_distribution'].items():
                print(f"  {category}: {count}")

        # Labels are already applied if args.apply_labels was set (handled in classifier)
        if args.apply_labels and not args.dry_run:
            print("\n✓ Labels applied successfully (see logs for details)")

        # Save report if requested
        if args.report:
            import json
            with open(args.report, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"Report saved to {args.report}")

        return 0

    except (ConfigurationError, GmailClientError, EmailClassifierError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in classify command: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_labels_command(args) -> int:
    """Handle label management command."""
    try:
        gmail_client = GmailClient(
            credentials_file=args.credentials,
            token_file=args.token,
            config_dir=args.config_dir
        )

        if args.list:
            labels = gmail_client.get_labels()
            print("Gmail Labels:")
            for name, label_id in sorted(labels.items()):
                print(f"  {name} ({label_id})")

        elif args.create:
            color_config = None
            if args.color:
                # Simple color mapping - extend as needed
                color_map = {
                    "red": {"textColor": "#ffffff", "backgroundColor": "#db4437"},
                    "blue": {"textColor": "#ffffff", "backgroundColor": "#4285f4"},
                    "green": {"textColor": "#ffffff", "backgroundColor": "#0f9d58"},
                    "yellow": {"textColor": "#000000", "backgroundColor": "#f4b400"},
                }
                color_config = color_map.get(args.color.lower())

            if args.dry_run:
                print(f"Would create label: {args.create}")
                if color_config:
                    print(f"  Color: {args.color}")
            else:
                label_id = gmail_client.create_label(args.create, color_config)
                print(f"Created label '{args.create}' with ID: {label_id}")

        elif args.delete:
            label_name = args.delete
            labels = gmail_client.get_labels()

            if label_name not in labels:
                print(f"Error: Label '{label_name}' not found.")
                print(f"Available labels: {', '.join(labels.keys())}")
                return 1

            label_id = labels[label_name]

            if args.dry_run:
                print(f"Would delete label: {label_name} (ID: {label_id})")
            else:
                try:
                    gmail_client.delete_label(label_id)
                    print(f"✓ Deleted label: {label_name}")
                except GmailClientError as e:
                    print(f"Error: {e}")
                    return 1

        else:
            print("No label operation specified. Use --list, --create, or --delete.")
            return 1

        return 0

    except GmailClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in labels command: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_migrate_command(args) -> int:
    """Handle migration from legacy code command."""
    try:
        migrator = LegacyMigrator(args.legacy_file)

        print(f"Migrating from: {args.legacy_file}")
        print(f"Output directory: {args.output_dir}")

        # Generate new configuration files
        base_config_path, custom_config_path = migrator.generate_new_config(args.output_dir)

        print(f"Created configuration files:")
        print(f"  Base config: {base_config_path}")
        print(f"  Custom config: {custom_config_path}")

        # Validate migration
        issues = migrator.validate_migration(args.output_dir)
        if issues:
            print(f"\nValidation Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nMigration validation: ✓ Passed")

        # Generate migration report
        if args.report:
            migrator.create_migration_report(args.report)
            print(f"Migration report saved to: {args.report}")

        return 0

    except Exception as e:
        logger.error(f"Migration error: {e}")
        print(f"Migration failed: {e}", file=sys.stderr)
        return 1


def handle_config_command(args) -> int:
    """Handle configuration management command."""
    try:
        config = Config(config_dir=args.config_dir)

        if args.validate:
            issues = config.validate()
            if issues:
                print("Configuration validation issues:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
            else:
                print("Configuration validation: ✓ Passed")

        elif args.show:
            import json
            config_dict = config.to_dict()
            print(json.dumps(config_dict, indent=2))

        elif args.export:
            import json
            config_dict = config.to_dict()
            with open(args.export, 'w') as f:
                json.dump(config_dict, f, indent=2)
            print(f"Configuration exported to: {args.export}")

        else:
            print("No configuration operation specified. Use --validate, --show, or --export.")
            return 1

        return 0

    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in config command: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_filters_command(args) -> int:
    """Handle Gmail filter management command."""
    try:
        # Load configuration
        config = Config(config_dir=args.config_dir)

        # Initialize Gmail client
        gmail_client = GmailClient(
            credentials_file=args.credentials,
            token_file=args.token,
            config_dir=args.config_dir
        )

        if args.list:
            filters = gmail_client.get_filters()
            print(f"Gmail Filters ({len(filters)} total):")
            for i, filter_data in enumerate(filters, 1):
                criteria = filter_data.get('criteria', {})
                actions = filter_data.get('action', {})

                print(f"\n{i}. Filter ID: {filter_data.get('id')}")
                print(f"   Criteria: {criteria}")
                print(f"   Actions: {actions}")

        elif args.summary:
            summary = gmail_client.list_filter_summary()
            print(f"Gmail Filters Summary:")
            print(f"  Total filters: {summary['total_filters']}")
            print(f"  Domain-based: {summary['filters_by_type']['domain_based']}")
            print(f"  Subject-based: {summary['filters_by_type']['subject_based']}")
            print(f"  Query-based: {summary['filters_by_type']['query_based']}")
            print(f"  Other: {summary['filters_by_type']['other']}")

            if args.report:
                import json
                with open(args.report, 'w') as f:
                    json.dump(summary, f, indent=2)
                print(f"\nDetailed report saved to: {args.report}")

        elif args.create:
            # Create filters for a specific category
            category_name = args.create
            if category_name not in config.categories:
                print(f"Error: Category '{category_name}' not found in configuration.")
                print(f"Available categories: {', '.join(config.categories.keys())}")
                return 1

            # Get or create the label for this category
            labels = gmail_client.get_labels()
            if category_name not in labels:
                if args.dry_run:
                    print(f"Would create label: {category_name}")
                else:
                    print(f"Creating label for category: {category_name}")
                    label_id = gmail_client.create_label(category_name)
                    labels[category_name] = label_id
            else:
                label_id = labels[category_name]

            if args.dry_run:
                print(f"Would create filters for category: {category_name}")
                category_config = config.categories[category_name]

                # Show what would be created
                domains = category_config.domains
                high_domains = domains.get('high_confidence', [])
                medium_domains = domains.get('medium_confidence', [])
                keywords = category_config.keywords.get('subject_high', [])

                estimated_filters = len(high_domains) + len(medium_domains)
                if keywords:
                    estimated_filters += (len(keywords) + 4) // 5  # Group of 5 keywords

                print(f"  Estimated filters to create: {estimated_filters}")
                print(f"  High confidence domains: {len(high_domains)}")
                print(f"  Medium confidence domains: {len(medium_domains)}")
                print(f"  Subject keyword groups: {(len(keywords) + 4) // 5 if keywords else 0}")
            else:
                print(f"Creating filters for category: {category_name}")
                category_config = config.categories[category_name]

                created_filters = gmail_client.create_category_filters(
                    category_name, category_config, label_id
                )

                print(f"✓ Successfully created {len(created_filters)} filters for '{category_name}'")
                print(f"  Filter IDs: {', '.join(created_filters)}")

        elif args.create_all:
            if args.dry_run:
                print("Would create filters for all categories:")
                for category_name in config.categories.keys():
                    print(f"  - {category_name}")
            else:
                print("Creating filters for all categories...")
                labels = gmail_client.get_labels()
                total_created = 0

                for category_name, category_config in config.categories.items():
                    print(f"\nProcessing category: {category_name}")

                    # Get or create label
                    if category_name not in labels:
                        print(f"  Creating label: {category_name}")
                        label_id = gmail_client.create_label(category_name)
                        labels[category_name] = label_id
                    else:
                        label_id = labels[category_name]

                    # Create filters
                    try:
                        created_filters = gmail_client.create_category_filters(
                            category_name, category_config, label_id
                        )
                        total_created += len(created_filters)
                        print(f"  ✓ Created {len(created_filters)} filters")
                    except Exception as e:
                        print(f"  ✗ Failed to create filters: {e}")

                print(f"\n✓ Total filters created: {total_created}")

        elif args.delete:
            filter_id = args.delete
            if args.dry_run:
                print(f"Would delete filter: {filter_id}")
            else:
                gmail_client.delete_filter(filter_id)
                print(f"✓ Deleted filter: {filter_id}")

        else:
            print("No filter operation specified. Use --list, --create, --create-all, --delete, or --summary.")
            return 1

        return 0

    except (ConfigurationError, GmailClientError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in filters command: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_reset_command(args) -> int:
    """Handle reset command for labels and filters."""
    try:
        # Initialize Gmail client
        gmail_client = GmailClient(
            credentials_file=args.credentials,
            token_file=args.token,
            config_dir=args.config_dir
        )

        # Determine what to reset
        reset_labels = args.all or args.labels
        reset_filters = args.all or args.filters

        if not reset_labels and not reset_filters:
            print("No reset target specified. Use --all, --labels, or --filters.")
            return 1

        # Generate backup filename if not provided
        backup_file = args.backup_to
        if not backup_file and (args.confirm or args.dry_run):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"reset_backup_{timestamp}.json"

        # Show preview in dry-run mode or if confirmation not provided
        if args.dry_run or not args.confirm:
            print("🔍 RESET PREVIEW")
            print("=" * 50)

            # Get known categories from configuration if available
            known_categories = None
            if reset_labels:
                try:
                    config = Config(config_dir=args.config_dir)
                    known_categories = list(config.categories.keys())
                except Exception as e:
                    logger.warning(f"Could not load category names: {e}")

            preview = gmail_client.get_reset_preview(
                include_labels=reset_labels,
                include_filters=reset_filters,
                category_pattern=args.category_pattern,
                known_categories=known_categories
            )

            if reset_labels and preview['labels']:
                labels_info = preview['labels']
                print(f"\n📋 LABELS TO RESET:")
                print(f"  Total labels: {labels_info['total_labels']}")
                print(f"  Matching pattern: {labels_info['matching_labels']}")
                print(f"  Labels: {', '.join(labels_info['labels_to_reset'])}")
                if labels_info.get('note'):
                    print(f"  ⚠️  {labels_info['note']}")

            if reset_filters and preview['filters']:
                filters_info = preview['filters']
                print(f"\n🔧 FILTERS TO RESET:")
                print(f"  Total filters: {filters_info['total_filters']}")
                print(f"  By type: {filters_info['filters_by_type']}")
                print(f"  Filter IDs: {len(filters_info['filters_to_delete'])} filters")

            if preview.get('warnings'):
                print(f"\n⚠️  WARNINGS:")
                for warning in preview['warnings']:
                    print(f"  - {warning}")

            if args.dry_run:
                print(f"\n🔍 DRY RUN: No changes were made")
                return 0
            elif not args.confirm:
                print(f"\n❌ CONFIRMATION REQUIRED")
                print(f"Add --confirm to proceed with reset")
                print(f"Backup will be saved to: {backup_file}")
                return 1

        # Proceed with actual reset
        print("🚨 PERFORMING RESET...")
        print("=" * 50)

        total_stats = {
            'labels': {},
            'filters': {},
            'backup_file': str(backup_file) if backup_file else None
        }

        # Reset filters
        if reset_filters:
            print("\n🔧 Resetting Gmail filters...")
            filter_stats = gmail_client.reset_all_filters(backup_to=backup_file)
            total_stats['filters'] = filter_stats

            print(f"✓ Deleted {filter_stats['deleted_filters']}/{filter_stats['total_filters']} filters")
            if filter_stats['failed_deletions'] > 0:
                print(f"⚠️  {filter_stats['failed_deletions']} filters failed to delete")

        # Reset labels
        if reset_labels:
            print("\n📋 Resetting category labels...")

            # Get known categories from configuration
            known_categories = None
            try:
                config = Config(config_dir=args.config_dir)
                known_categories = list(config.categories.keys())
            except Exception as e:
                logger.warning(f"Could not load category names: {e}")

            label_stats = gmail_client.reset_category_labels(
                category_pattern=args.category_pattern,
                backup_to=backup_file if backup_file and not reset_filters else None,
                known_categories=known_categories
            )
            total_stats['labels'] = label_stats

            print(f"📋 Found {label_stats['matching_labels']} matching labels")
            if label_stats.get('note'):
                print(f"ℹ️  {label_stats['note']}")

            if label_stats['matching_labels'] > 0:
                deleted_count = label_stats.get('deleted_labels', 0)
                if deleted_count > 0:
                    print(f"✅ Successfully deleted {deleted_count} labels")

                failed_count = label_stats.get('failed_deletions', 0)
                if failed_count > 0:
                    print(f"⚠️  {failed_count} labels could not be deleted (likely system labels)")
                    print("   System labels (Inbox, Sent, etc.) cannot be deleted via API")

        # Save reset report
        if backup_file:
            import json
            report_file = str(backup_file).replace('.json', '_report.json')
            with open(report_file, 'w') as f:
                json.dump(total_stats, f, indent=2)
            print(f"\n📄 Reset report saved to: {report_file}")

        print("\n✅ RESET COMPLETE")
        return 0

    except (GmailClientError,) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in reset command: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_cache_command(args) -> int:
    """Handle cache management command."""
    try:
        # Initialize cache
        cache_dir = args.config_dir / "cache"
        from .core.email_cache import EmailCache
        cache = EmailCache(cache_dir)

        if args.stats:
            # Show cache statistics
            stats = cache.get_classification_stats()
            print("\n📊 Email Classification Cache Statistics")
            print("=" * 50)
            print(f"Total processed emails: {stats.get('total_processed', 0):,}")
            print(f"Total classified emails: {stats.get('total_classified', 0):,}")
            print(f"Total labeled emails: {stats.get('total_labeled', 0):,}")
            print(f"Pending labels: {stats.get('pending_labels', 0):,}")
            print(f"Classification rate: {stats.get('classification_rate', 0):.1%}")
            print(f"Labeling rate: {stats.get('labeling_rate', 0):.1%}")

            if stats.get('category_distribution'):
                print(f"\nCategory Distribution:")
                for category, count in stats['category_distribution'].items():
                    print(f"  {category}: {count:,}")

        elif args.apply_labels:
            # Apply labels to cached classified emails
            print("Applying labels from cache...")

            # Initialize Gmail client
            gmail_client = GmailClient(
                credentials_file=args.credentials,
                token_file=args.token,
                config_dir=args.config_dir
            )

            # Get unlabeled classified emails
            unlabeled_emails = cache.get_unlabeled_classified_emails()
            if not unlabeled_emails:
                print("No unlabeled classified emails found in cache.")
                return 0

            print(f"Found {len(unlabeled_emails)} emails with pending labels\n")

            # Get current labels
            labels = gmail_client.get_labels()
            applied_count = 0
            total_emails = len(unlabeled_emails)

            for message_id, category, confidence in unlabeled_emails:
                try:
                    # Create label if needed
                    if category not in labels:
                        print(f"Creating label: {category}")
                        gmail_client.create_label(category)
                        labels = gmail_client.get_labels()  # Refresh

                    # Fetch email details for display
                    try:
                        message = gmail_client.get_message(message_id)
                        if message:
                            email = message  # message is already an Email object
                            subject = email.headers.subject[:80] + "..." if len(email.headers.subject) > 80 else email.headers.subject
                            sender = email.headers.from_address[:50] + "..." if len(email.headers.from_address) > 50 else email.headers.from_address

                            # Show progress with email details
                            print(f"[{applied_count + 1}/{total_emails}] Labeling: {category} (confidence: {confidence:.2f})")
                            print(f"  From: {sender}")
                            print(f"  Subject: {subject}")
                    except Exception as fetch_error:
                        # If fetch fails, still show progress
                        print(f"[{applied_count + 1}/{total_emails}] Labeling: {category} (confidence: {confidence:.2f})")
                        print(f"  Message ID: {message_id}")

                    # Apply label
                    label_id = labels[category]
                    gmail_client.add_label(message_id, label_id)

                    # Mark as labeled in cache
                    cache.mark_labeled(message_id)
                    applied_count += 1

                except Exception as e:
                    logger.warning(f"Failed to apply label to {message_id}: {e}")
                    print(f"  ✗ Failed: {e}")

            print(f"\n✓ Successfully applied labels to {applied_count}/{total_emails} emails")

        elif args.export:
            # Export cached classifications
            cache.export_classifications(args.export)
            print(f"Exported classifications to {args.export}")

        elif args.cleanup:
            # Cleanup old cache entries
            deleted_count = cache.cleanup_old_entries(args.cleanup)
            print(f"Cleaned up {deleted_count} old cache entries (older than {args.cleanup} days)")

        else:
            print("Please specify an action: --stats, --apply-labels, --export, or --cleanup")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Cache command failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        import logging
        setup_root_logger(logging.DEBUG)
    else:
        import logging
        setup_root_logger(logging.INFO)

    # Show dry-run warning
    if getattr(args, 'dry_run', False):
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    # Handle commands
    if args.command == "classify":
        return handle_classify_command(args)
    elif args.command == "labels":
        return handle_labels_command(args)
    elif args.command == "migrate":
        return handle_migrate_command(args)
    elif args.command == "config":
        return handle_config_command(args)
    elif args.command == "filters":
        return handle_filters_command(args)
    elif args.command == "reset":
        return handle_reset_command(args)
    elif args.command == "cache":
        return handle_cache_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())