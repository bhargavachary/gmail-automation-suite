#!/usr/bin/env python3
"""
Gmail Automation Suite - Advanced Usage Examples

This script demonstrates advanced features including:
- Semi-supervised learning
- Custom topic modeling
- Batch processing
- Performance optimization
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gmail_automation import GmailAutomationUnified

def advanced_setup():
    """Advanced setup with custom configuration"""
    print("🔧 Advanced Gmail Automation Setup")
    print("=" * 40)

    # Initialize with extended label system and custom topic count
    automation = GmailAutomationUnified(
        credentials_file='credentials.json',
        token_file='token.json',
        use_ml=True,
        n_topics=12  # Custom topic count for fine-grained analysis
    )

    # Authenticate
    if not automation.authenticate():
        print("❌ Authentication failed")
        return False

    # Use extended system for advanced users
    automation.labels = automation.extended_labels
    print("📋 Using extended label system (10 categories)")

    return automation

def high_performance_scanning(automation):
    """Demonstrate high-performance concurrent scanning"""
    print("\n⚡ High-Performance Concurrent Scanning")
    print("=" * 45)

    from gmail_automation import IncrementalScanConfig

    # Configure for high-performance scanning
    config = IncrementalScanConfig(
        max_emails=0,           # Unlimited
        days_back=30,           # Last 30 days
        only_unlabeled=True,    # Only unlabeled emails (faster)
        exclude_system_labels=True,
        use_concurrent=True,
        max_workers=8           # High concurrency
    )

    print("🚀 Starting concurrent scan with 8 workers...")
    automation.scan_and_label_emails_incremental(config)

def semi_supervised_learning_demo():
    """Demonstrate semi-supervised learning workflow"""
    print("\n🧠 Semi-Supervised Learning Demo")
    print("=" * 40)

    try:
        from email_clustering_reviewer import EmailClusteringReviewer

        print("📊 This would normally start an interactive review session")
        print("💡 Run this command for actual review:")
        print("   python gmail_automation.py --review-clusters --cluster-count 10")

        print("\n🎯 Benefits of semi-supervised learning:")
        print("   • 10x faster than individual email review")
        print("   • Active learning focuses on uncertain predictions")
        print("   • Continuous model improvement")
        print("   • Batch corrections for efficiency")

    except ImportError:
        print("⚠️ Semi-supervised learning module not available")

def custom_topic_modeling_demo(automation):
    """Demonstrate custom topic modeling"""
    print("\n🔍 Custom Topic Modeling Demo")
    print("=" * 35)

    if automation.ml_categorizer and automation.ml_categorizer.n_topics:
        print(f"🎯 Using custom topic count: {automation.ml_categorizer.n_topics}")
        print("📈 This allows for:")
        print("   • Fine-grained topic discovery")
        print("   • Custom granularity based on email volume")
        print("   • Better categorization for specific domains")
    else:
        print("🔍 Using auto-detected topic count")
        print("📊 System will automatically determine optimal number of topics")

def batch_processing_demo():
    """Demonstrate batch processing capabilities"""
    print("\n📦 Batch Processing Demo")
    print("=" * 30)

    commands = [
        "# Daily maintenance (fast)",
        "python gmail_automation.py --scan-unlabeled --days-back 1 --concurrent",
        "",
        "# Weekly comprehensive scan",
        "python gmail_automation.py --scan-emails --days-back 7 --concurrent --max-workers 8",
        "",
        "# Monthly deep learning review",
        "python gmail_automation.py --review-clusters --cluster-count 15",
        "",
        "# Quarterly full rescan",
        "python gmail_automation.py --scan-all-unlabeled --concurrent --max-workers 8"
    ]

    print("📋 Recommended batch processing schedule:")
    for cmd in commands:
        if cmd.startswith("#"):
            print(f"\n{cmd}")
        elif cmd:
            print(f"   {cmd}")
        else:
            print()

def performance_optimization_tips():
    """Show performance optimization tips"""
    print("\n🚀 Performance Optimization Tips")
    print("=" * 40)

    tips = [
        "💡 Use --concurrent for 3-5x speed improvement",
        "⚡ Use --scan-unlabeled for maintenance (10x faster)",
        "🎯 Adjust --max-workers based on system capacity",
        "📊 Use --debug-categorization to identify bottlenecks",
        "🔄 Regular --review-clusters sessions improve accuracy",
        "💾 Enable session resumption for large scans",
        "🏷️ Start with consolidated system, upgrade to extended if needed"
    ]

    for tip in tips:
        print(f"   {tip}")

def main():
    """Main advanced demonstration"""
    print("Gmail Automation Suite - Advanced Usage Examples")
    print("=" * 60)

    try:
        # Advanced setup
        automation = advanced_setup()
        if not automation:
            return 1

        # Demonstrate advanced features
        custom_topic_modeling_demo(automation)
        semi_supervised_learning_demo()
        batch_processing_demo()
        performance_optimization_tips()

        print("\n✅ Advanced usage demonstration completed!")
        print("\n🚀 Ready for high-performance email automation!")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())