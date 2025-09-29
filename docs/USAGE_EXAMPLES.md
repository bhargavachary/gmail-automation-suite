# Gmail Automation Suite - Usage Examples

This document provides comprehensive examples for using the Gmail Automation Suite across different scenarios and use cases.

## 🚀 Quick Start Workflows

### Complete Setup and First Run
```bash
# 1. Initial setup and authentication
gmail-automation config --validate

# 2. Classify recent emails using ML ensemble
gmail-automation classify --method hybrid --query "newer_than:7d" --max-emails 100 --apply-labels

# 3. Create server-side filters for automatic processing
gmail-automation --dry-run filters --create-all  # Preview first
gmail-automation filters --create-all             # Apply filters

# 4. Check the results
gmail-automation filters --summary --report initial_setup_report.json
```

### Daily Email Processing
```bash
#!/bin/bash
# daily_email_processing.sh

echo "🌅 Daily Gmail Processing - $(date)"

# Process emails from the last day
gmail-automation classify \
    --method hybrid \
    --query "newer_than:1d" \
    --max-emails 200 \
    --apply-labels \
    --report "daily_$(date +%Y%m%d).json"

# Check filter effectiveness
gmail-automation filters --summary >> daily_filter_log.txt

echo "✅ Daily processing complete"
```

## 📊 Classification Scenarios

### 1. **High-Volume Email Classification**
```bash
# Process large batches efficiently
gmail-automation classify \
    --method hybrid \
    --query "newer_than:30d" \
    --max-emails 5000 \
    --apply-labels \
    --report monthly_classification.json \
    --verbose

# Monitor progress with chunked processing
for week in {0..4}; do
    start_day=$((week * 7))
    end_day=$(((week + 1) * 7))

    gmail-automation classify \
        --method hybrid \
        --query "newer_than:${end_day}d older_than:${start_day}d" \
        --max-emails 1000 \
        --apply-labels \
        --report "week_${week}_classification.json"
done
```

### 2. **Specific Domain Processing**
```bash
# Process all emails from financial institutions
gmail-automation classify \
    --method rule_based \
    --query "from:(bank.com OR creditcard.com OR paypal.com)" \
    --apply-labels \
    --report financial_emails.json

# Process shopping receipts
gmail-automation classify \
    --method hybrid \
    --query "from:(amazon.com OR flipkart.com OR myntra.com)" \
    --max-emails 500 \
    --apply-labels

# Process security alerts
gmail-automation classify \
    --method rule_based \
    --query "subject:(security OR alert OR suspicious OR login)" \
    --apply-labels \
    --report security_alerts.json
```

### 3. **Method Comparison and Optimization**
```bash
# Compare different classification methods
for method in rule_based ml hybrid; do
    echo "Testing method: $method"

    gmail-automation classify \
        --method $method \
        --query "newer_than:7d" \
        --max-emails 100 \
        --report "comparison_${method}.json"
done

# Analyze results
python -c "
import json
import sys

methods = ['rule_based', 'ml', 'hybrid']
for method in methods:
    with open(f'comparison_{method}.json') as f:
        data = json.load(f)
        print(f'{method}: {data.get(\"classification_rate\", 0):.1%} success rate')
"
```

## 🔧 Filter Management

### 1. **Progressive Filter Deployment**
```bash
# Start with high-priority categories
gmail-automation filters --create "🏦 Finance & Bills"
gmail-automation filters --create "🔔 Security & Alerts"

# Test effectiveness for a few days, then add more
gmail-automation filters --create "🛒 Purchases & Receipts"
gmail-automation filters --create "✈️ Services & Subscriptions"

# Finally add marketing and personal
gmail-automation filters --create "📰 Promotions & Marketing"
gmail-automation filters --create "👤 Personal & Social"
```

### 2. **Filter Performance Monitoring**
```bash
#!/bin/bash
# filter_monitoring.sh

echo "📈 Filter Performance Report - $(date)"

# Generate current filter summary
gmail-automation filters --summary --report "filter_summary_$(date +%Y%m%d).json"

# Compare with previous week
if [ -f "filter_summary_$(date -d '7 days ago' +%Y%m%d).json" ]; then
    echo "📊 Week-over-week comparison:"

    current=$(cat "filter_summary_$(date +%Y%m%d).json" | jq '.total_filters')
    previous=$(cat "filter_summary_$(date -d '7 days ago' +%Y%m%d).json" | jq '.total_filters')

    echo "Filters: $previous → $current ($(($current - $previous)) change)"
fi

# Check for filter conflicts or issues
gmail-automation filters --list | grep -i "error\|conflict" || echo "✅ No filter issues detected"
```

### 3. **Category-Specific Filter Management**
```bash
# Create filters only for work-related categories
work_categories=("🏦 Finance & Bills" "🔔 Security & Alerts" "✈️ Services & Subscriptions")

for category in "${work_categories[@]}"; do
    echo "Creating filters for: $category"
    gmail-automation --dry-run filters --create "$category"

    # Confirm before proceeding
    read -p "Proceed with $category? (y/n): " confirm
    if [[ $confirm == "y" ]]; then
        gmail-automation filters --create "$category"
    fi
done
```

## 🏷️ Label Management

### 1. **Organized Label Creation**
```bash
# Create color-coded labels for different purposes
gmail-automation labels --create "🏦 Finance & Bills" --color red
gmail-automation labels --create "🛒 Purchases & Receipts" --color green
gmail-automation labels --create "🔔 Security & Alerts" --color yellow
gmail-automation labels --create "✈️ Services & Subscriptions" --color blue

# Create sub-labels for organization
gmail-automation labels --create "🏦 Finance & Bills/Banking"
gmail-automation labels --create "🏦 Finance & Bills/Credit Cards"
gmail-automation labels --create "🏦 Finance & Bills/Investments"
```

### 2. **Label Audit and Cleanup**
```bash
# List all labels for review
gmail-automation labels --list > current_labels.txt

# Show label usage statistics
echo "📊 Label Analysis:"
gmail-automation labels --list | wc -l | xargs echo "Total labels:"

# Find unused labels (would require additional implementation)
# gmail-automation --dry-run reset --labels --category-pattern "Old.*"
```

## 🔄 Reset and Maintenance

### 1. **Safe Reset Procedures**
```bash
# Always preview before resetting
gmail-automation --dry-run reset --all

# Progressive reset - filters first, then labels
gmail-automation reset --filters --confirm --backup-to backup_filters.json

# Wait and verify everything works, then reset labels if needed
gmail-automation reset --labels --confirm --backup-to backup_labels.json

# Reset with specific patterns (glob-style patterns supported)
gmail-automation --dry-run reset --labels --category-pattern "*"         # All labels (preview)
gmail-automation reset --labels --category-pattern "Test*" --confirm     # Labels starting with "Test"
gmail-automation reset --labels --category-pattern "*temp*" --confirm    # Labels containing "temp"
gmail-automation reset --labels --category-pattern "Old_*" --confirm     # Labels starting with "Old_"

# Complete reset with comprehensive backup
gmail-automation reset --all --confirm --backup-to complete_backup_$(date +%Y%m%d).json
```

### 2. **Maintenance Workflows**
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "🔧 Weekly Gmail Automation Maintenance"

# 1. Backup current configuration
gmail-automation config --export "config_backup_$(date +%Y%m%d).json"

# 2. Validate system health
gmail-automation config --validate || echo "⚠️ Configuration issues detected"

# 3. Clean up old filters if needed
filter_count=$(gmail-automation filters --summary | grep "Total filters" | grep -o '[0-9]\+')
if [ "$filter_count" -gt 100 ]; then
    echo "⚠️ High filter count detected: $filter_count"
    echo "Consider reviewing and consolidating filters"
fi

# 4. Performance check
gmail-automation classify --method hybrid --max-emails 10 --report health_check.json

echo "✅ Maintenance complete"
```

### 3. **Disaster Recovery**
```bash
# Restore from backup after issues
gmail-automation reset --all --confirm

# Restore configuration
gmail-automation config --import config_backup_20241201.json

# Recreate filters from backup
# gmail-automation filters --restore backup_filters.json  # Future feature

# Verify restoration
gmail-automation config --validate
gmail-automation filters --summary
```

## 🎯 Advanced Use Cases

### 1. **Multi-Account Management**
```bash
#!/bin/bash
# multi_account_processing.sh

accounts=("work" "personal" "business")

for account in "${accounts[@]}"; do
    echo "Processing account: $account"

    # Switch credentials and token
    cp "credentials_${account}.json" credentials.json
    cp "token_${account}.json" token.json

    # Process emails for this account
    gmail-automation classify \
        --method hybrid \
        --query "newer_than:7d" \
        --max-emails 100 \
        --apply-labels \
        --report "${account}_classification.json"

    # Create filters if not already done
    gmail-automation --dry-run filters --create-all
done
```

### 2. **Custom Business Rules**
```bash
# Process emails for specific projects
gmail-automation classify \
    --method rule_based \
    --query "subject:(project OR client OR proposal) newer_than:30d" \
    --apply-labels

# Handle urgent emails
gmail-automation classify \
    --method hybrid \
    --query "is:important OR subject:(urgent OR asap OR emergency)" \
    --apply-labels \
    --report urgent_emails.json

# Process newsletters and subscriptions
gmail-automation classify \
    --method ml \
    --query "from:(newsletter OR subscribe OR noreply)" \
    --max-emails 500 \
    --apply-labels
```

### 3. **Integration with External Tools**
```bash
#!/bin/bash
# integration_workflow.sh

# 1. Process emails and generate report
gmail-automation classify \
    --method hybrid \
    --query "newer_than:1d" \
    --max-emails 200 \
    --apply-labels \
    --report daily_report.json

# 2. Extract key metrics
important_emails=$(jq '.category_distribution."🔔 Security & Alerts"' daily_report.json)
finance_emails=$(jq '.category_distribution."🏦 Finance & Bills"' daily_report.json)

# 3. Send notification if high priority emails detected
if [ "$important_emails" -gt 5 ]; then
    echo "⚠️ High number of security alerts: $important_emails" | \
        mail -s "Gmail Alert Summary" admin@company.com
fi

# 4. Update dashboard or monitoring system
curl -X POST "https://dashboard.company.com/api/gmail-stats" \
    -H "Content-Type: application/json" \
    -d @daily_report.json
```

## 📈 Performance Optimization

### 1. **Batch Processing Strategies**
```bash
# Process in time-based chunks for better performance
for month in {1..12}; do
    start_date="2024-$(printf "%02d" $month)-01"
    end_date="2024-$(printf "%02d" $((month + 1)))-01"

    gmail-automation classify \
        --method hybrid \
        --query "after:$start_date before:$end_date" \
        --max-emails 1000 \
        --apply-labels \
        --report "month_$(printf "%02d" $month)_2024.json"

    # Small delay to avoid rate limiting
    sleep 10
done
```

### 2. **Efficient Query Patterns**
```bash
# Use specific queries to reduce processing load
gmail-automation classify \
    --method rule_based \
    --query "from:(bank OR financial OR credit) newer_than:30d" \
    --apply-labels

# Process unread emails first (usually most important)
gmail-automation classify \
    --method hybrid \
    --query "is:unread newer_than:7d" \
    --max-emails 200 \
    --apply-labels

# Handle attachments separately (often receipts/documents)
gmail-automation classify \
    --method hybrid \
    --query "has:attachment newer_than:30d" \
    --max-emails 500 \
    --apply-labels
```

### 3. **Monitoring and Alerting**
```bash
#!/bin/bash
# monitoring_script.sh

# Check classification success rate
success_rate=$(gmail-automation classify \
    --method hybrid \
    --max-emails 50 \
    --report test_classification.json \
    --dry-run | grep "Classification rate" | grep -o '[0-9]\+%')

echo "Current classification success rate: $success_rate"

# Alert if success rate drops below threshold
if [[ "${success_rate%?}" -lt 85 ]]; then
    echo "⚠️ Classification success rate below threshold: $success_rate"
    echo "Consider retraining models or updating rules"
fi

# Check filter effectiveness
filter_summary=$(gmail-automation filters --summary)
total_filters=$(echo "$filter_summary" | grep "Total filters" | grep -o '[0-9]\+')

echo "Active filters: $total_filters"

# Log performance metrics
echo "$(date): Success Rate: $success_rate, Filters: $total_filters" >> performance_log.txt
```

## 🔍 Troubleshooting Examples

### 1. **Authentication Issues**
```bash
# Reset authentication completely
rm token.json
gmail-automation config --validate

# Test with minimal permissions
gmail-automation classify --method rule_based --max-emails 1 --verbose

# Check OAuth scope issues
gmail-automation config --show | grep -i scope
```

### 2. **Classification Problems**
```bash
# Test different methods to isolate issues
for method in rule_based ml hybrid; do
    echo "Testing $method:"
    gmail-automation classify \
        --method $method \
        --max-emails 5 \
        --verbose \
        --report "debug_${method}.json"
done

# Check model availability
ls -la data/backups/*/

# Validate configuration
gmail-automation config --validate --verbose
```

### 3. **Performance Issues**
```bash
# Profile classification performance
time gmail-automation classify \
    --method hybrid \
    --max-emails 10 \
    --verbose

# Check memory usage during processing
(gmail-automation classify --method ml --max-emails 100 --verbose) &
PID=$!
while kill -0 $PID 2>/dev/null; do
    ps -p $PID -o pid,vsz,rss,pcpu
    sleep 5
done
```

## 📋 Automation Scripts

### 1. **Cron Job Setup**
```bash
# Add to crontab for automated processing
# crontab -e

# Process emails every 6 hours
0 */6 * * * /path/to/venv/bin/gmail-automation classify --method hybrid --query "newer_than:6h" --max-emails 100 --apply-labels

# Daily filter summary
0 9 * * * /path/to/venv/bin/gmail-automation filters --summary --report /path/to/daily_filter_report.json

# Weekly maintenance
0 6 * * 1 /path/to/weekly_maintenance.sh
```

### 2. **Systemd Service**
```ini
# /etc/systemd/system/gmail-automation.service
[Unit]
Description=Gmail Automation Service
After=network.target

[Service]
Type=oneshot
ExecStart=/path/to/venv/bin/gmail-automation classify --method hybrid --query "newer_than:1h" --max-emails 50 --apply-labels
User=your-username
WorkingDirectory=/path/to/gmail-automation

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/gmail-automation.timer
[Unit]
Description=Run Gmail Automation every hour
Requires=gmail-automation.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. **Docker Integration**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# Run classification on container start
CMD ["gmail-automation", "classify", "--method", "hybrid", "--max-emails", "100", "--apply-labels"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  gmail-automation:
    build: .
    volumes:
      - ./data:/app/data
      - ./credentials.json:/app/credentials.json
      - ./token.json:/app/token.json
    environment:
      - PYTHONUNBUFFERED=1
    command: >
      sh -c "
        gmail-automation classify --method hybrid --max-emails 200 --apply-labels &&
        gmail-automation filters --summary --report /app/data/docker_summary.json
      "
```

---

*These examples cover common usage patterns for the Gmail Automation Suite. For more advanced configurations and troubleshooting, see the [ML Ensemble Guide](ML_ENSEMBLE_GUIDE.md) and main [README.md](../README.md).*