# Gmail Automation Suite v3.0

🚀 A comprehensive, streamlined tool for Gmail management that automates label creation, filter setup, email migration, and inbox organization with OAuth 2.0 security.

## ✨ Features

- 🏷️ **Smart Label Creation**: Creates organized labels with custom colors
- 🔍 **Advanced Filters**: Auto-categorizes emails with importance marking and archiving
- 📧 **Email Migration**: Batch migrate emails between labels with rate limiting
- 🗑️ **Label Management**: Delete old labels and consolidate email organization
- 🧹 **Filter Cleanup**: Clear existing filters for fresh setup
- 📊 **Promotional Email Scanning**: Identifies and manages promotional emails
- ✅ **Comprehensive Validation**: Environment validation and robust error handling
- 🚀 **Modular Operations**: Run individual operations or complete automation

## Quick Start

### 1. Setup Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials and save as `credentials.json`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Automation

```bash
# Full automation (labels + filters)
python gmail_automation.py

# Labels only
python gmail_automation.py --labels-only

# Filters only (with importance marking and auto-archive)
python gmail_automation.py --filters-only

# Clear existing filters and create new ones
python gmail_automation.py --filters-only --clear-filters

# Advanced operations
python gmail_automation.py --scan-promos                    # Scan promotional emails
python gmail_automation.py --migrate-labels "Old Label" "New Label"  # Migrate emails
python gmail_automation.py --delete-labels "Label1" "Label2"         # Delete labels
python gmail_automation.py --clear-filters                           # Clear all filters
```

## Labels Created

- 🏦 Banking & Finance (Blue - #4a86e8)
- 📈 Investments & Trading (Green - #16a766)
- 🔔 Alerts & Security (Red - #cc3a21)
- 🛒 Shopping & Orders (Orange - #ffad47)
- 👤 Personal & Work (Purple - #8e63ce)
- 📰 Marketing & News (Gray - #666666)
- 🎯 Action Required (Bright Red - #fb4c2f)
- 📦 Receipts & Archive (Light Gray - #cccccc)
- 🏥 Insurance & Services (Light Green - #43d692)
- ✈️ Travel & Transport (Yellow - #fad165)

*Note: Colors use Gmail's official API palette for guaranteed compatibility*

## 🔥 Enhanced Smart Filters

The automation creates intelligent filters with advanced capabilities:

- **Auto-categorization**: Emails from known senders and content patterns
- **Importance Marking**: Critical emails (banking, security, investments) marked as important
- **Smart Archiving**: Routine notifications auto-archived to keep inbox clean
- **Batch Processing**: Efficient email migration with rate limiting
- **Advanced Queries**: Complex Gmail search syntax for precise filtering
- **Category Coverage**: Banking, shopping, travel, security, news, and more

### Filter Categories with Special Features:

- 🏦 **Banking & Finance** - Marked important, includes investment platforms
- 🔔 **Alerts & Security** - Marked important, stays in inbox
- 📈 **Investments & Trading** - Marked important, trading confirmations
- 🛒 **Shopping & Orders** - Order tracking and delivery notifications
- 📦 **Receipts & Archive** - Bills and subscription confirmations
- 🏥 **Insurance & Services** - Health and insurance communications
- 📰 **Marketing & News** - Newsletters and promotional content
- ✈️ **Travel & Transport** - Tickets and booking confirmations

## File Structure

```
gmail_api_automation/
├── gmail_automation.py     # Main automation script
├── requirements.txt        # Python dependencies
├── credentials.json        # OAuth credentials (you provide)
├── token.json             # Auto-generated after first run
├── backup/                # Old scripts (moved here)
└── README.md              # This file
```

## 🛠️ Command Line Options

```bash
python gmail_automation.py [OPTIONS]

Basic Options:
  --credentials FILE    Path to credentials file (default: credentials.json)
  --token FILE         Path to token file (default: token.json)
  --labels-only        Only create labels, skip filters
  --filters-only       Only create filters, skip labels
  --scan-promos        Scan for promotional emails

Advanced Operations:
  --clear-filters              Clear all existing filters
  --migrate-labels FROM TO     Migrate emails from one label to another
  --delete-labels LABEL...     Delete specified labels
  -h, --help                   Show help message

Examples:
  # Full setup with filter cleanup
  python gmail_automation.py --clear-filters

  # Migrate old labels to new organization
  python gmail_automation.py --migrate-labels "Old Banking" "🏦 Banking & Finance"

  # Clean up unused labels
  python gmail_automation.py --delete-labels "Label_19" "Label_20" "Old Label"

  # Fresh filter setup
  python gmail_automation.py --filters-only --clear-filters
```

## Security & Privacy

- Uses OAuth 2.0 for secure authentication
- Requires explicit user consent for Gmail access
- Stores minimal credentials locally
- No data transmitted to external servers

## Troubleshooting

**Authentication Issues:**
- Ensure `credentials.json` is valid OAuth 2.0 credentials
- Delete `token.json` and re-authenticate if needed

**Permission Errors:**
- Verify Gmail API is enabled in Google Cloud Console
- Check OAuth consent screen configuration

**Rate Limiting:**
- Script includes delays to avoid API rate limits
- Re-run if you encounter temporary rate limit errors
