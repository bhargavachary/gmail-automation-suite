# Gmail Automation Suite v5.1 - Complete Usage Guide

## 🚀 Quick Start

```bash
# 1. Create labels
python gmail_automation.py --labels-only

# 2. Scan and label emails
python gmail_automation.py --scan-emails

# 3. Review and improve with semi-supervised learning
python gmail_automation.py --review-clusters
```

## 📧 Email Operations

### Basic Scanning
```bash
# Scan all emails (last 30 days, max 1000)
python gmail_automation.py --scan-emails

# Scan specific timeframe
python gmail_automation.py --scan-emails --days-back 7 --max-emails 500

# Unlimited scanning
python gmail_automation.py --scan-emails --max-emails 0 --days-back 0
```

### Incremental Labeling (Maintenance)
```bash
# Only label unlabeled emails (much faster)
python gmail_automation.py --scan-unlabeled

# Daily maintenance
python gmail_automation.py --scan-unlabeled --days-back 1

# Complete unlabeled scan
python gmail_automation.py --scan-all-unlabeled
```

## ⚡ High-Performance Options

### Concurrent Processing
```bash
# Use multithreading (default: 4 workers)
python gmail_automation.py --scan-emails --concurrent

# Custom worker count
python gmail_automation.py --scan-unlabeled --concurrent --max-workers 8

# High-performance unlimited scan
python gmail_automation.py --scan-all-unlabeled --concurrent --max-workers 8
```

## 🧠 AI/ML Features

### Machine Learning
```bash
# Show ML model status
python gmail_automation.py --ml-info

# Bootstrap initial ML training
python gmail_automation.py --bootstrap-training

# Debug AI categorization decisions
python gmail_automation.py --scan-emails --debug-categorization

# Disable ML (rule-based only)
python gmail_automation.py --scan-emails --disable-ml
```

### Semi-Supervised Learning (NEW!)
```bash
# Interactive cluster review for corrections
python gmail_automation.py --review-clusters

# Custom review settings
python gmail_automation.py --review-clusters --cluster-count 15 --confidence-threshold 0.7

# Review more emails for better clustering
python gmail_automation.py --review-clusters --review-emails 500
```

## 🎯 Semi-Supervised Learning Workflow

The semi-supervised learning feature helps improve accuracy through human feedback:

### 1. Start Review Session
```bash
python gmail_automation.py --review-clusters
```

### 2. Review Process
- System collects emails with low-medium confidence (uncertainty sampling)
- Groups similar emails into clusters using AI embeddings
- You review clusters instead of individual emails (much faster!)
- Confirm correct predictions or provide corrections
- Export training data automatically

### 3. Example Review Session
```
📦 CLUSTER 1/10 (ID: 0)
   📊 8 emails, Confidence: 0.42
   🤖 Predicted: 🛒 Shopping & Orders

📧 Sample emails in this cluster:
   1. From: Bandhan Mutual Fund
      Subject: Confirmation of Purchase processed in Folio No 6860742

   2. From: SBI Mutual Fund
      Subject: Transaction Confirmation - SIP Investment

🤔 Is '🛒 Shopping & Orders' correct for this cluster?
Enter: (y)es / (n)o / new category / 'skip' / 'quit' / 'info': n

📝 Enter the correct category:
   2. 📈 Investments & Trading  ← Select this one!

✅ Corrected to: 📈 Investments & Trading
```

### 4. Benefits
- **10x faster than individual review** - Batch corrections
- **Active learning** - Focuses on uncertain predictions
- **Continuous improvement** - Each session makes AI smarter
- **Export training data** - Use corrections for model retraining

## 📊 Command Line Options Reference

### Core Operations
- `--labels-only` - Create labels only
- `--scan-emails` - Scan and label all emails
- `--scan-unlabeled` - Scan only unlabeled emails (incremental)
- `--scan-all-unlabeled` - Scan ALL unlabeled emails (unlimited)

### Processing Control
- `--max-emails N` - Maximum emails to process (0 = unlimited)
- `--days-back N` - Days back to scan (0 = all)
- `--concurrent` - Use multithreaded processing
- `--max-workers N` - Number of concurrent threads

### AI/ML Features
- `--debug-categorization` - Show AI decision process
- `--disable-ml` - Use rule-based categorization only
- `--ml-info` - Show ML model status
- `--bootstrap-training` - Train initial ML model

### Semi-Supervised Learning
- `--review-clusters` - Interactive cluster review
- `--cluster-count N` - Number of clusters for review
- `--confidence-threshold X` - Max confidence for uncertainty sampling
- `--review-emails N` - Number of emails to include in clustering

## 🎯 Best Practices

### Initial Setup
1. **Create labels**: `python gmail_automation.py --labels-only`
2. **Bootstrap ML**: `python gmail_automation.py --bootstrap-training`
3. **Initial scan**: `python gmail_automation.py --scan-emails --concurrent`

### Maintenance Workflow
1. **Daily**: `python gmail_automation.py --scan-unlabeled --days-back 1 --concurrent`
2. **Weekly review**: `python gmail_automation.py --review-clusters`
3. **Monthly deep scan**: `python gmail_automation.py --scan-all-unlabeled --concurrent`

### Performance Tips
- Use `--concurrent` for faster processing
- Use `--scan-unlabeled` for maintenance (10x faster)
- Use `--review-clusters` to improve accuracy over time
- Use `--max-emails 0` for unlimited processing when needed

## 🏷️ Labels Created

The system creates these organized labels:

- 🏦 **Banking & Finance** (Blue) - Banks, payments, invoices
- 📈 **Investments & Trading** (Green) - Stocks, mutual funds, trading
- 🔔 **Alerts & Security** (Red) - Security alerts, urgent notifications
- 🛒 **Shopping & Orders** (Orange) - Orders, deliveries, receipts
- 👤 **Personal & Work** (Purple) - Personal communications, work emails
- 📰 **Marketing & News** (Gray) - Newsletters, marketing, news
- 🎯 **Action Required** (Bright Red) - Emails requiring immediate action
- 📦 **Receipts & Archive** (Light Gray) - Bills, confirmations, archives
- 🏥 **Insurance & Services** (Light Green) - Insurance, health, services
- ✈️ **Travel & Transport** (Yellow) - Travel, tickets, bookings

## 🔧 Troubleshooting

### Authentication Issues
- Ensure `credentials.json` is valid OAuth 2.0 credentials
- Delete `token.json` and re-authenticate if needed

### ML Issues
- Install dependencies: `pip install -r requirements.txt`
- Check ML status: `python gmail_automation.py --ml-info`

### Performance Issues
- Use `--concurrent` for faster processing
- Reduce `--max-emails` if experiencing timeouts
- Use `--scan-unlabeled` for maintenance scans

### Semi-Supervised Learning Issues
- Install clustering dependencies: `pip install scikit-learn matplotlib seaborn`
- Adjust `--confidence-threshold` if no emails found for review
- Use `--review-emails` to increase sample size

---

**💡 Pro Tip**: Combine features for maximum efficiency:
```bash
python gmail_automation.py --scan-all-unlabeled --concurrent --max-workers 8 --debug-categorization
```