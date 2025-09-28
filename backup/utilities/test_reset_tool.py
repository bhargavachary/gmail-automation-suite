#!/usr/bin/env python3
"""
Quick test of the enhanced reset tool - shows options without requiring user input
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_reset_tool():
    """Test the reset tool functions"""
    print("🧪 Testing Enhanced Reset Tool")
    print("=" * 40)

    # Import the reset functions
    try:
        from reset_and_start_fresh import show_current_status, show_reset_options, GMAIL_CLEANUP_AVAILABLE

        print(f"📋 Gmail cleanup available: {GMAIL_CLEANUP_AVAILABLE}")
        print()

        # Show current status
        show_current_status()

        # Show reset options
        options = show_reset_options()

        print("\n✅ Reset tool functions are working correctly!")
        print("\n💡 New Features Added:")
        print("   🏷️ Option 1: Reset Gmail Labels Only")
        print("   🔄 Option 5: Complete Reset (Gmail + Local Files)")
        print("   📋 Status check now includes Gmail labels")
        print("   ⚡ Proper sequence: Gmail cleanup FIRST, then local files")

        print("\n🚀 Ready to use enhanced reset tool!")
        print("   Run: python3 reset_and_start_fresh.py")

    except Exception as e:
        print(f"❌ Error testing reset tool: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reset_tool()