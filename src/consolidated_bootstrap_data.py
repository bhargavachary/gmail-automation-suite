#!/usr/bin/env python3
"""
Consolidated Bootstrap Training Data Generator

Creates synthetic training data for the new 6-category Gmail automation system.
Based on real-world email patterns and user requirements.
"""

import json
import datetime
from typing import List, Dict

def create_consolidated_bootstrap_data() -> List[Dict]:
    """Create comprehensive bootstrap training data for consolidated 6-category system"""

    training_data = []

    # 🏦 Finance & Bills - Core financial management
    finance_examples = [
        # Bank transaction alerts
        {
            'email_data': {
                'sender': 'alerts@axisbank.com',
                'subject': 'INR 154.00 was debited from your A/c no. XX2191',
                'snippet': 'Dear Customer, Here is the summary of your transaction: Amount Debited: INR 154.00 Transaction ID: 123456789 Available Balance: INR 25,000'
            },
            'category': '🏦 Finance & Bills'
        },
        {
            'email_data': {
                'sender': 'HDFC Bank InstaAlerts <alerts@hdfcbank.net>',
                'subject': 'Rs.70.00 debited via Credit Card **1080',
                'snippet': 'Rs.70.00 is debited from your HDFC Bank Credit Card ending 1080 towards Razorpay*Swiggy on 28 Sep 2025 at 09:12:53'
            },
            'category': '🏦 Finance & Bills'
        },
        {
            'email_data': {
                'sender': 'cc.statements@hdfcbank.net',
                'subject': 'Your HDFC Bank Credit Card Statement is ready',
                'snippet': 'Dear Customer, Your HDFC Bank Credit Card Statement for the period ending 28 Sep 2025 is now available. Total Amount Due: Rs. 5,432'
            },
            'category': '🏦 Finance & Bills'
        },
        {
            'email_data': {
                'sender': 'ebill.mobility@jio.com',
                'subject': 'E-Bill for Jio Number 7578xxxxx767',
                'snippet': 'Hi Mr. D KUMAR BHARGAV ACHARY Your bill for 7578008767 is ₹ 706.82 Due date 02 Oct 2025'
            },
            'category': '🏦 Finance & Bills'
        },
        {
            'email_data': {
                'sender': 'intimations@cpc.incometax.gov.in',
                'subject': 'ITR Intimation under section 143(1) - PAN: XXXXX1234X',
                'snippet': 'Dear Taxpayer, Processing of your Income Tax Return for Assessment Year 2025-26 has been completed under section 143(1)'
            },
            'category': '🏦 Finance & Bills'
        },
        # Investment & SIP alerts
        {
            'email_data': {
                'sender': 'investorcare@icicipruamc.com',
                'subject': 'SIP Transaction Confirmation - ICICI Prudential Large Cap Fund',
                'snippet': 'Dear Investor, Your SIP transaction of Rs. 5000 in ICICI Prudential Large Cap Fund has been processed successfully'
            },
            'category': '🏦 Finance & Bills'
        },
        {
            'email_data': {
                'sender': 'Bandhan Mutual Fund <enq_g@cam',
                'subject': 'Confirmation of Purchase processed in Folio No 6860742',
                'snippet': 'Dear Investor, Purchase of Rs 2000.00 in Bandhan Core Equity Fund - Regular Plan - Growth has been processed on 28-Sep-2025'
            },
            'category': '🏦 Finance & Bills'
        }
    ]

    # 🛒 Purchases & Receipts - E-commerce lifecycle
    shopping_examples = [
        {
            'email_data': {
                'sender': 'order-update@amazon.in',
                'subject': 'Your order has been shipped',
                'snippet': 'Good news! Your order #407-3925347-3239523 containing Nothing Phone (3a) has been shipped and will arrive by Oct 1, 2025'
            },
            'category': '🛒 Purchases & Receipts'
        },
        {
            'email_data': {
                'sender': 'no-reply@rmt.flipkart.com',
                'subject': 'Nothing Phone (3a) from your order has been delivered',
                'snippet': 'Flipkart.com Item Delivered Hi DK Bhargav Achary, An item has been delivered. Order placed on Sep 22, 2025'
            },
            'category': '🛒 Purchases & Receipts'
        },
        {
            'email_data': {
                'sender': 'noreply@swiggy.in',
                'subject': 'Your Swiggy order has been delivered!',
                'snippet': 'Order #SW123456789 from Dominos Pizza has been delivered. Total: ₹650. Hope you enjoyed your meal!'
            },
            'category': '🛒 Purchases & Receipts'
        },
        {
            'email_data': {
                'sender': 'no_reply@email.apple.com',
                'subject': 'Your receipt from Apple',
                'snippet': 'Thank you for your purchase from Apple. Receipt for Order: M123456789 Date: 28 Sep 2025 MacBook Air M2 - ₹99,900'
            },
            'category': '🛒 Purchases & Receipts'
        },
        {
            'email_data': {
                'sender': 'Amazon.in <payments-messages@amazon.in>',
                'subject': 'Refund processed for order #407-3925347-3239523',
                'snippet': 'Your refund of ₹1,299 for Nothing Phone (3a) case has been processed and will reflect in your account within 3-5 business days'
            },
            'category': '🛒 Purchases & Receipts'
        },
        {
            'email_data': {
                'sender': 'myntra@myntra.com',
                'subject': 'Tax Invoice for Order #MYN123456',
                'snippet': 'GST Invoice for your Myntra order. Order Date: 28 Sep 2025 Invoice Number: MYN/2025/123456 Total Amount: ₹2,499'
            },
            'category': '🛒 Purchases & Receipts'
        }
    ]

    # ✈️ Services & Subscriptions - Recurring services & bookings
    services_examples = [
        {
            'email_data': {
                'sender': 'info@account.netflix.com',
                'subject': 'Your Netflix membership will renew tomorrow',
                'snippet': 'Hi Bhargav, Your Netflix membership will automatically renew on 29 Sep 2025 for ₹649/month. No action needed.'
            },
            'category': '✈️ Services & Subscriptions'
        },
        {
            'email_data': {
                'sender': 'noreply@makemytrip.com',
                'subject': 'Flight Booking Confirmation - PNR: ABC123',
                'snippet': 'Your flight booking is confirmed! Mumbai to Delhi on 15 Oct 2025. PNR: ABC123 E-ticket attached. Have a safe journey!'
            },
            'category': '✈️ Services & Subscriptions'
        },
        {
            'email_data': {
                'sender': 'no-reply@mail.1mg.com',
                'subject': 'Lab Test Reports Available - Order #1MG123456',
                'snippet': 'Your lab test reports for Complete Blood Count and Lipid Profile are now available. Login to 1mg to view and download'
            },
            'category': '✈️ Services & Subscriptions'
        },
        {
            'email_data': {
                'sender': 'PartnerCare@policybazaar.com',
                'subject': 'Policy Renewal Reminder - Car Insurance',
                'snippet': 'Your car insurance policy expires on 05 Oct 2025. Renew now to avoid policy lapse and continue your protection'
            },
            'category': '✈️ Services & Subscriptions'
        },
        {
            'email_data': {
                'sender': 'support@spotify.com',
                'subject': 'Spotify Premium subscription renewed',
                'snippet': 'Thanks for being a Spotify Premium member! Your subscription has been renewed for ₹119/month. Keep enjoying ad-free music'
            },
            'category': '✈️ Services & Subscriptions'
        },
        {
            'email_data': {
                'sender': 'bookings@oyo.com',
                'subject': 'Booking Confirmed - OYO 123456',
                'snippet': 'Your booking at OYO Hotel Mumbai is confirmed for 20-22 Oct 2025. Check-in: 2 PM, Check-out: 12 PM. Booking ID: OYO123456'
            },
            'category': '✈️ Services & Subscriptions'
        }
    ]

    # 🔔 Security & Alerts - Critical account security
    security_examples = [
        {
            'email_data': {
                'sender': 'no-reply@dropbox.com',
                'subject': 'New sign in to your Dropbox account',
                'snippet': 'Hi Bhargav, A new computer just signed in to your Dropbox account. Device: MacBook Pro, Location: Mumbai, India. If this was not you, secure your account immediately'
            },
            'category': '🔔 Security & Alerts'
        },
        {
            'email_data': {
                'sender': 'appleid.apple.com',
                'subject': 'Your Apple ID was used to sign in to iCloud',
                'snippet': 'Your Apple ID was used to sign in to iCloud on a MacBook Pro. Date: 28 Sep 2025, 2:30 PM IST. If this was not you, change your password'
            },
            'category': '🔔 Security & Alerts'
        },
        {
            'email_data': {
                'sender': 'security@facebookmail.com',
                'subject': 'Security alert: New login from Chrome on Mac',
                'snippet': 'We noticed a new login to your Facebook account from Chrome on Mac in Mumbai, Maharashtra. If this was not you, please secure your account'
            },
            'category': '🔔 Security & Alerts'
        },
        {
            'email_data': {
                'sender': 'noreply-location-sharing@google.com',
                'subject': 'Location sharing reminder',
                'snippet': 'You are sharing your location with Family Group. This sharing will continue until you turn it off. Manage your location sharing settings'
            },
            'category': '🔔 Security & Alerts'
        },
        {
            'email_data': {
                'sender': 'account-security@amazon.in',
                'subject': 'Verify your account - Unusual activity detected',
                'snippet': 'We detected unusual activity on your Amazon account. For your security, please verify your account by clicking the link below'
            },
            'category': '🔔 Security & Alerts'
        },
        {
            'email_data': {
                'sender': 'security@github.com',
                'subject': 'Password changed for your GitHub account',
                'snippet': 'Your GitHub password was changed on 28 Sep 2025 at 14:30 UTC from IP address 103.x.x.x. If you did not make this change, contact support'
            },
            'category': '🔔 Security & Alerts'
        }
    ]

    # 📰 Promotions & Marketing - Sales, offers, newsletters
    marketing_examples = [
        {
            'email_data': {
                'sender': 'from@cred.club',
                'subject': 'Festive Offer: Get ₹500 cashback on your next credit card payment',
                'snippet': 'This festive season, get ₹500 cashback when you pay your credit card bill through CRED. Limited time offer. Terms apply'
            },
            'category': '📰 Promotions & Marketing'
        },
        {
            'email_data': {
                'sender': 'information@hdfcbank.net',
                'subject': 'Pre-approved Personal Loan of ₹5 Lakhs awaits you',
                'snippet': 'Congratulations! You are eligible for a pre-approved personal loan of up to ₹5,00,000 at attractive interest rates. Apply now'
            },
            'category': '📰 Promotions & Marketing'
        },
        {
            'email_data': {
                'sender': 'messages-noreply@linkedin.com',
                'subject': 'Weekly digest: 5 jobs matching your profile',
                'snippet': 'Here are the top job opportunities for you this week: Senior Software Engineer at Google, Product Manager at Microsoft, and 3 more'
            },
            'category': '📰 Promotions & Marketing'
        },
        {
            'email_data': {
                'sender': 'News@insideapple.apple.com',
                'subject': 'iPhone 15 Pro Max - Now available in India',
                'snippet': 'The most advanced iPhone ever is here. iPhone 15 Pro Max with titanium design and A17 Pro chip. Pre-order starts today'
            },
            'category': '📰 Promotions & Marketing'
        },
        {
            'email_data': {
                'sender': 'offers@flipkart.com',
                'subject': 'Big Billion Days Sale: Up to 80% off everything',
                'snippet': 'The biggest sale of the year is here! Get up to 80% off on electronics, fashion, home, and more. Sale starts 1st October. Unsubscribe anytime'
            },
            'category': '📰 Promotions & Marketing'
        },
        {
            'email_data': {
                'sender': 'newsletter@techcrunch.com',
                'subject': 'TechCrunch Daily: OpenAI launches new model',
                'snippet': 'Good morning! Here are the top tech stories today: OpenAI announces GPT-5, Tesla opens new Gigafactory, and more tech news'
            },
            'category': '📰 Promotions & Marketing'
        }
    ]

    # 👤 Personal & Social - Direct communication & social
    personal_examples = [
        {
            'email_data': {
                'sender': 'biswa.uce@gmail.com',
                'subject': 'Gentle reminder: Team dinner tonight',
                'snippet': 'Hi Bhargav, Just a gentle reminder about our team dinner tonight at 7 PM at The Bombay Canteen. Looking forward to seeing you there!'
            },
            'category': '👤 Personal & Social'
        },
        {
            'email_data': {
                'sender': 'notifications@linkedin.com',
                'subject': 'Rahul Sharma commented on your post',
                'snippet': 'Rahul Sharma commented on your post about "AI in Healthcare": "Great insights! Would love to discuss this further." View comment'
            },
            'category': '👤 Personal & Social'
        },
        {
            'email_data': {
                'sender': 'noreply@facebookmail.com',
                'subject': 'Priya tagged you in a photo',
                'snippet': 'Priya tagged you in a photo from your college reunion. Check out the photo and see who else was tagged. View on Facebook'
            },
            'category': '👤 Personal & Social'
        },
        {
            'email_data': {
                'sender': 'calendar-notification@google.com',
                'subject': 'Meeting with client tomorrow at 10 AM',
                'snippet': 'You have a meeting scheduled with XYZ Corp tomorrow at 10:00 AM. Location: Office Conference Room A. Prepare presentation slides'
            },
            'category': '👤 Personal & Social'
        },
        {
            'email_data': {
                'sender': 'noreply@medium.com',
                'subject': 'Your friend Amit shared an article with you',
                'snippet': 'Your friend Amit shared "The Future of Machine Learning" with you on Medium. "Thought you might find this interesting!"'
            },
            'category': '👤 Personal & Social'
        },
        {
            'email_data': {
                'sender': 'invitations@zoom.us',
                'subject': 'You are invited to join family video call',
                'snippet': 'Mom has invited you to join a Zoom meeting: "Family catch-up call". Time: Today 8:00 PM IST. Meeting ID: 123-456-789'
            },
            'category': '👤 Personal & Social'
        }
    ]

    # Combine all examples
    all_examples = (
        finance_examples + shopping_examples + services_examples +
        security_examples + marketing_examples + personal_examples
    )

    # Add metadata to each example
    for example in all_examples:
        example['metadata'] = {
            'source': 'consolidated_bootstrap',
            'created_date': datetime.datetime.now().isoformat(),
            'system': 'consolidated_6_category'
        }

    return all_examples

def save_bootstrap_data(filename: str = None):
    """Save bootstrap data to JSON file"""
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"consolidated_bootstrap_training_{timestamp}.json"

    data = create_consolidated_bootstrap_data()

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(data)} bootstrap training examples to {filename}")

    # Show category distribution
    from collections import Counter
    categories = [item['category'] for item in data]
    distribution = Counter(categories)

    print("\n📊 Category distribution:")
    for category, count in sorted(distribution.items()):
        print(f"   {category}: {count} examples")

    return filename

def create_extended_bootstrap_examples():
    """Create additional examples for extended 10-category system"""
    extended_examples = [
        # 📈 Investments & Trading
        {
            'email_data': {
                'sender': 'trading@zerodha.com',
                'subject': 'Stock purchase confirmation - RELIANCE',
                'snippet': 'Your order to buy 10 shares of RELIANCE at ₹2,450 has been executed successfully. Contract note attached.'
            },
            'category': '📈 Investments & Trading',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        {
            'email_data': {
                'sender': 'portfolio@groww.in',
                'subject': 'Monthly portfolio report - September 2025',
                'snippet': 'Your portfolio gained 12.5% this month. Current value: ₹2,45,000. View detailed performance report.'
            },
            'category': '📈 Investments & Trading',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        # 🎯 Action Required
        {
            'email_data': {
                'sender': 'support@booking.com',
                'subject': 'Urgent: Action required for your booking',
                'snippet': 'Your hotel booking needs immediate attention. Please confirm your stay dates to avoid cancellation.'
            },
            'category': '🎯 Action Required',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        {
            'email_data': {
                'sender': 'hr@company.com',
                'subject': 'Action Required: Complete your annual review',
                'snippet': 'Please complete your annual performance review by October 5th. Link expires in 3 days.'
            },
            'category': '🎯 Action Required',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        # 🏥 Insurance & Services
        {
            'email_data': {
                'sender': 'care@maxlifeinsurance.com',
                'subject': 'Policy premium due reminder',
                'snippet': 'Your life insurance policy premium of ₹12,000 is due on 15 Oct 2025. Pay now to continue coverage.'
            },
            'category': '🏥 Insurance & Services',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        {
            'email_data': {
                'sender': 'support@apollo247.com',
                'subject': 'Health checkup appointment confirmed',
                'snippet': 'Your health checkup is scheduled for Oct 5, 2025 at 10:00 AM. Please carry valid ID and be fasting.'
            },
            'category': '🏥 Insurance & Services',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        # ✈️ Travel & Transport (separated from Services)
        {
            'email_data': {
                'sender': 'tickets@airindia.in',
                'subject': 'Flight ticket confirmation - AI 131',
                'snippet': 'Your flight from Mumbai to Delhi on 20 Oct 2025 is confirmed. PNR: ABC123. Web check-in available 24 hours before departure.'
            },
            'category': '✈️ Travel & Transport',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        },
        {
            'email_data': {
                'sender': 'bookings@uber.com',
                'subject': 'Trip receipt - Mumbai Airport',
                'snippet': 'Thank you for riding with Uber. Trip cost: ₹420. From: Home to Mumbai Airport. Duration: 45 minutes.'
            },
            'category': '✈️ Travel & Transport',
            'metadata': {
                'source': 'extended_bootstrap',
                'created_date': datetime.datetime.now().isoformat(),
                'system': 'extended_10_category'
            }
        }
    ]

    return extended_examples

if __name__ == "__main__":
    # --- (Your existing code for the 6-category dataset is perfect) ---
    print("Creating consolidated 6-category bootstrap dataset...")
    save_bootstrap_data("consolidated_bootstrap_training_6_categories.json")


    # --- MODIFIED LOGIC FOR 10-CATEGORY DATASET ---
    print("\nCreating extended 10-category bootstrap dataset...")
    consolidated_data = create_consolidated_bootstrap_data()
    extended_examples = create_extended_bootstrap_examples()

    # Define a more intelligent re-mapping function for services
    def remap_services_category(item: dict) -> str:
        subject = item['email_data']['subject'].lower()
        snippet = item['email_data']['snippet'].lower()

        # Check for Travel keywords
        if any(kw in subject or kw in snippet for kw in ['flight', 'pnr', 'booking confirmed', 'oyo']):
            return '✈️ Travel & Transport'

        # Check for Insurance/Health keywords
        if any(kw in subject or kw in snippet for kw in ['policy', 'insurance', 'lab test', 'reports available']):
            return '🏥 Insurance & Services'

        # Default for other subscriptions (Netflix, Spotify)
        return '📦 Receipts & Archive'


    # Map existing categories
    for item in consolidated_data:
        old_category = item['category']

        if old_category == '✈️ Services & Subscriptions':
            item['category'] = remap_services_category(item)
        elif old_category == '🏦 Finance & Bills':
            # Check for investment keywords to separate them
            subject = item['email_data']['subject'].lower()
            if 'sip' in subject or 'mutual fund' in subject or 'folio' in subject:
                item['category'] = '📈 Investments & Trading'
            else:
                item['category'] = '🏦 Banking & Finance'
        elif old_category == '🛒 Purchases & Receipts':
            item['category'] = '🛒 Shopping & Orders'
        elif old_category == '🔔 Security & Alerts':
            item['category'] = '🔔 Alerts & Security'
        elif old_category == '📰 Promotions & Marketing':
            item['category'] = '📰 Marketing & News'
        elif old_category == '👤 Personal & Social':
            item['category'] = '👤 Personal & Work'

        item['metadata']['system'] = 'extended_10_category'

    # Combine datasets
    extended_dataset = consolidated_data + extended_examples

    # --- (The rest of your saving and distribution code is perfect) ---
    # Save extended dataset
    extended_filename = "extended_bootstrap_training_10_categories.json"
    with open(extended_filename, 'w', encoding='utf-8') as f:
        json.dump(extended_dataset, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(extended_dataset)} extended training examples to {extended_filename}")

    # Show category distribution for extended
    from collections import Counter
    categories = [item['category'] for item in extended_dataset]
    distribution = Counter(categories)

    print("\n📊 Extended system category distribution:")
    for category, count in sorted(distribution.items()):
        print(f"   {category}: {count} examples")