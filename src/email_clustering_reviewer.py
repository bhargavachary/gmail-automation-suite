#!/usr/bin/env python3
"""
Email Clustering Reviewer - Semi-Supervised Learning Enhancement

Interactive tool for reviewing, correcting, and improving email categorization
through human-in-the-loop machine learning.

Features:
- Cluster emails by similarity for batch review
- Interactive correction interface
- Active learning for model improvement
- Confidence-based uncertainty sampling
- Export corrected labels for retraining
"""

import json
import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import datetime
try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.manifold import TSNE
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

@dataclass
class EmailCluster:
    """Represents a cluster of similar emails"""
    cluster_id: int
    emails: List[Dict]
    predicted_category: str
    confidence: float
    suggested_category: Optional[str] = None
    human_verified: bool = False
    review_notes: str = ""

@dataclass
class ReviewSession:
    """Tracks a human review session"""
    session_id: str
    start_time: datetime.datetime
    emails_reviewed: int = 0
    corrections_made: int = 0
    clusters_completed: int = 0
    confidence_threshold: float = 0.7

class EmailClusteringReviewer:
    """Semi-supervised learning system for email categorization improvement"""

    def __init__(self, gmail_automation=None):
        self.gmail_automation = gmail_automation
        self.sentence_transformer = None
        self.clusters = []
        self.review_sessions = []
        self.corrections_database = []

        # Initialize embeddings model
        if EMBEDDINGS_AVAILABLE:
            try:
                self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Sentence transformer initialized for clustering")
            except Exception as e:
                print(f"⚠️ Could not initialize sentence transformer: {e}")

    def collect_emails_for_review(self, max_emails: int = 200,
                                min_confidence: float = 0.0,
                                max_confidence: float = 0.8) -> List[Dict]:
        """
        Collect emails that need human review based on confidence scores

        Args:
            max_emails: Maximum number of emails to collect
            min_confidence: Minimum confidence to include
            max_confidence: Maximum confidence to include (for uncertainty sampling)

        Returns:
            List of emails with metadata for review
        """
        print(f"🔍 Collecting emails for review (confidence: {min_confidence:.2f}-{max_confidence:.2f})")

        if not self.gmail_automation:
            print("❌ Gmail automation not available")
            return []

        # Get recent unlabeled emails for review
        emails_to_review = []

        # Sample from recently processed emails with low-medium confidence
        # This creates uncertainty sampling for active learning
        try:
            # Get some emails from inbox for testing clustering
            query = "in:inbox"
            result = self.gmail_automation.service.users().messages().list(
                userId='me',
                maxResults=max_emails,
                q=query
            ).execute()

            message_ids = [msg['id'] for msg in result.get('messages', [])]

            for i, msg_id in enumerate(message_ids[:max_emails]):
                try:
                    email = self.gmail_automation.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ).execute()

                    # Extract email data
                    headers = {h['name'].lower(): h['value']
                             for h in email.get('payload', {}).get('headers', [])}

                    email_data = {
                        'id': msg_id,
                        'sender': headers.get('from', ''),
                        'subject': headers.get('subject', ''),
                        'snippet': email.get('snippet', ''),
                        'date': headers.get('date', ''),
                        'body': self._extract_email_body(email)
                    }

                    # Get current categorization with confidence
                    if self.gmail_automation.use_ml and self.gmail_automation.ml_categorizer:
                        try:
                            result = self.gmail_automation.ml_categorizer.hybrid_categorize(email_data)
                            predicted_category = result.get('final_category', 'Unknown')
                            confidence = result.get('final_confidence', 0.5)
                        except:
                            predicted_category = self.gmail_automation._categorize_email_rule_based(email_data)
                            confidence = 0.3  # Low confidence for rule-based
                    else:
                        predicted_category = self.gmail_automation._categorize_email_rule_based(email_data)
                        confidence = 0.3

                    # Include if confidence is in target range
                    if min_confidence <= confidence <= max_confidence:
                        email_data.update({
                            'predicted_category': predicted_category,
                            'confidence': confidence,
                            'current_labels': email.get('labelIds', [])
                        })
                        emails_to_review.append(email_data)

                    if i % 50 == 0:
                        print(f"   📊 Processed {i+1}/{len(message_ids)} emails for review...")

                except Exception as e:
                    print(f"   ⚠️ Error processing email {i+1}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Error collecting emails: {e}")
            return []

        print(f"✅ Collected {len(emails_to_review)} emails for review")
        return emails_to_review

    def create_email_clusters(self, emails: List[Dict], n_clusters: int = 10) -> List[EmailCluster]:
        """
        Cluster emails by similarity for batch review

        Args:
            emails: List of email dictionaries
            n_clusters: Number of clusters to create

        Returns:
            List of EmailCluster objects
        """
        if not SKLEARN_AVAILABLE:
            print("❌ Cannot create clusters: scikit-learn not available")
            print("💡 Install with: pip install scikit-learn")
            return []

        if not self.sentence_transformer or not emails:
            print("❌ Cannot create clusters: missing transformer or emails")
            return []

        print(f"🔄 Creating {n_clusters} email clusters from {len(emails)} emails...")

        # Create embeddings for clustering
        email_texts = []
        for email in emails:
            text = f"{email['subject']} {email['snippet']} {email['sender']}"
            email_texts.append(text)

        # Generate embeddings
        print("   🤖 Generating embeddings...")
        embeddings = self.sentence_transformer.encode(email_texts)

        # Handle edge case of very few emails
        if n_clusters <= 1 or len(emails) < 2:
            print(f"   💡 Too few emails for clustering ({len(emails)} emails, need at least 2)")
            # Create a single cluster with all emails

            # Determine predicted category (most common)
            categories = [email.get('predicted_category', 'Unknown') for email in emails]
            predicted_category = max(set(categories), key=categories.count) if categories else 'Unknown'

            # Calculate average confidence
            confidences = [email.get('confidence', 0.0) for email in emails]
            avg_confidence = np.mean(confidences) if confidences else 0.0

            cluster = EmailCluster(
                cluster_id=0,
                emails=emails,
                predicted_category=predicted_category,
                confidence=avg_confidence
            )
            return [cluster]

        # Perform clustering
        print("   🎯 Performing K-means clustering...")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        # Calculate silhouette score only if we have valid clusters
        if n_clusters > 1 and len(set(cluster_labels)) > 1:
            silhouette_avg = silhouette_score(embeddings, cluster_labels)
            print(f"   📊 Clustering silhouette score: {silhouette_avg:.3f}")
        else:
            print(f"   📊 Single cluster created - no silhouette score calculated")

        # Create cluster objects
        clusters = []
        for cluster_id in range(n_clusters):
            cluster_emails = [emails[i] for i in range(len(emails)) if cluster_labels[i] == cluster_id]

            if not cluster_emails:
                continue

            # Determine cluster's predicted category (most common)
            categories = [email['predicted_category'] for email in cluster_emails]
            predicted_category = max(set(categories), key=categories.count)

            # Calculate average confidence
            confidences = [email['confidence'] for email in cluster_emails]
            avg_confidence = np.mean(confidences)

            cluster = EmailCluster(
                cluster_id=cluster_id,
                emails=cluster_emails,
                predicted_category=predicted_category,
                confidence=avg_confidence
            )
            clusters.append(cluster)

        # Sort clusters by confidence (lowest first for review priority)
        clusters.sort(key=lambda x: x.confidence)

        print(f"✅ Created {len(clusters)} clusters")
        return clusters

    def start_interactive_review(self, clusters: List[EmailCluster]) -> ReviewSession:
        """
        Start interactive review session for cluster correction

        Args:
            clusters: List of email clusters to review

        Returns:
            ReviewSession object with results
        """
        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session = ReviewSession(
            session_id=session_id,
            start_time=datetime.datetime.now()
        )

        print(f"\n🎯 Starting Interactive Review Session: {session_id}")
        print("=" * 60)
        print("📋 Instructions:")
        print("   - Review each cluster of similar emails")
        print("   - Confirm or correct the predicted category")
        print("   - Type 'skip' to skip a cluster")
        print("   - Type 'quit' to end session")
        print("   - Type 'info' to see category options")
        print("=" * 60)

        available_categories = [
            "🏦 Banking & Finance",
            "📈 Investments & Trading",
            "🔔 Alerts & Security",
            "🛒 Shopping & Orders",
            "👤 Personal & Work",
            "📰 Marketing & News",
            "🎯 Action Required",
            "📦 Receipts & Archive",
            "🏥 Insurance & Services",
            "✈️ Travel & Transport"
        ]

        for i, cluster in enumerate(clusters):
            print(f"\n📦 CLUSTER {i+1}/{len(clusters)} (ID: {cluster.cluster_id})")
            print(f"   📊 {len(cluster.emails)} emails, Confidence: {cluster.confidence:.3f}")
            print(f"   🤖 Predicted: {cluster.predicted_category}")
            print("\n📧 Sample emails in this cluster:")

            # Show sample emails from cluster
            for j, email in enumerate(cluster.emails[:3]):
                sender_short = email['sender'].split('@')[0] if '@' in email['sender'] else email['sender'][:30]
                subject_short = email['subject'][:50] + "..." if len(email['subject']) > 50 else email['subject']
                print(f"   {j+1}. From: {sender_short[:25]}")
                print(f"      Subject: {subject_short}")
                if j < 2 and len(cluster.emails) > 1:
                    print()

            if len(cluster.emails) > 3:
                print(f"   ... and {len(cluster.emails) - 3} more similar emails")

            # Get user input
            while True:
                print(f"\n🤔 Is '{cluster.predicted_category}' correct for this cluster?")
                user_input = input("   Enter: (y)es / (n)o / new category / 'skip' / 'quit' / 'info': ").strip().lower()

                if user_input == 'quit':
                    print("🛑 Review session ended by user")
                    return session
                elif user_input == 'skip':
                    print("⏭️ Skipping cluster...")
                    break
                elif user_input == 'info':
                    print("\n📋 Available categories:")
                    for cat in available_categories:
                        print(f"   • {cat}")
                    continue
                elif user_input in ['y', 'yes']:
                    cluster.human_verified = True
                    cluster.suggested_category = cluster.predicted_category
                    print("✅ Category confirmed!")
                    session.emails_reviewed += len(cluster.emails)
                    break
                elif user_input in ['n', 'no']:
                    print("\n📝 Enter the correct category:")
                    for j, cat in enumerate(available_categories):
                        print(f"   {j+1}. {cat}")

                    cat_input = input("   Enter category number or full name: ").strip()

                    # Parse input
                    correct_category = None
                    if cat_input.isdigit():
                        idx = int(cat_input) - 1
                        if 0 <= idx < len(available_categories):
                            correct_category = available_categories[idx]
                    else:
                        # Try to match by name
                        for cat in available_categories:
                            if cat_input.lower() in cat.lower():
                                correct_category = cat
                                break

                    if correct_category:
                        cluster.suggested_category = correct_category
                        cluster.human_verified = True
                        session.emails_reviewed += len(cluster.emails)
                        session.corrections_made += len(cluster.emails)
                        print(f"✅ Corrected to: {correct_category}")

                        # Store correction for training
                        for email in cluster.emails:
                            self.corrections_database.append({
                                'email_data': email,
                                'original_prediction': cluster.predicted_category,
                                'corrected_category': correct_category,
                                'session_id': session_id,
                                'timestamp': datetime.datetime.now().isoformat()
                            })
                        break
                    else:
                        print("❌ Invalid category. Please try again.")
                        continue
                else:
                    # Try direct category input
                    for cat in available_categories:
                        if user_input.lower() in cat.lower():
                            cluster.suggested_category = cat
                            cluster.human_verified = True
                            session.emails_reviewed += len(cluster.emails)
                            session.corrections_made += len(cluster.emails)
                            print(f"✅ Set to: {cat}")

                            # Store correction for training
                            for email in cluster.emails:
                                self.corrections_database.append({
                                    'email_data': email,
                                    'original_prediction': cluster.predicted_category,
                                    'corrected_category': cat,
                                    'session_id': session_id,
                                    'timestamp': datetime.datetime.now().isoformat()
                                })
                            break
                    else:
                        print("❌ Category not recognized. Please try again.")
                        continue
                    break

            session.clusters_completed += 1

        # Save corrections
        self._save_corrections(session_id)

        print(f"\n🎉 Review session completed!")
        print(f"   📊 Emails reviewed: {session.emails_reviewed}")
        print(f"   ✏️ Corrections made: {session.corrections_made}")
        print(f"   📦 Clusters completed: {session.clusters_completed}")

        # Ask user what to do with the reviewed data
        if session.corrections_made > 0:
            print(f"\n🤖 You made {session.corrections_made} corrections!")
            print("❓ What would you like to do with the reviewed data?")
            print("   1. 🧠 Retrain and improve the model with corrections")
            print("   2. 💾 Just save the reviewed data (no retraining)")
            print("   3. 🔍 Show me the corrections first, then decide")

            choice = input("\n👉 Enter your choice (1/2/3): ").strip()

            if choice == "1":
                self._retrain_model_with_corrections(session_id)
            elif choice == "2":
                print("💾 Corrections saved for future use")
                self._export_training_data_summary(session_id)
            elif choice == "3":
                self._show_corrections_summary(session_id)
                # Ask again after showing corrections
                retrain_choice = input("\n❓ Now retrain the model? (y/N): ").strip().lower()
                if retrain_choice in ['y', 'yes']:
                    self._retrain_model_with_corrections(session_id)
                else:
                    print("💾 Corrections saved for future use")
                    self._export_training_data_summary(session_id)
            else:
                print("💾 Invalid choice - corrections saved for future use")
                self._export_training_data_summary(session_id)
        else:
            print("\n💡 No corrections were made in this session")

        return session

    def export_training_data(self, session_id: Optional[str] = None) -> str:
        """Export corrected emails as training data"""
        corrections = self.corrections_database
        if session_id:
            corrections = [c for c in corrections if c['session_id'] == session_id]

        # Determine appropriate data directory
        data_dirs = ['../data/training', 'data/training', '.']
        save_dir = '.'

        for data_dir in data_dirs:
            if os.path.exists(data_dir):
                save_dir = data_dir
                break

        filename = os.path.join(save_dir, f"corrected_training_data_{session_id or 'all'}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        training_data = []
        for correction in corrections:
            training_data.append({
                'email_data': correction['email_data'],  # Keep full email data for ML training
                'category': correction['corrected_category'],
                'metadata': {
                    'original_prediction': correction['original_prediction'],
                    'session_id': correction['session_id'],
                    'timestamp': correction['timestamp'],
                    'source': 'semi_supervised_correction'
                }
            })

        with open(filename, 'w') as f:
            json.dump(training_data, f, indent=2)

        print(f"✅ Exported {len(training_data)} training samples to {filename}")
        return filename

    def _extract_email_body(self, email: Dict) -> str:
        """Extract body text from Gmail message"""
        def get_body_recursive(payload):
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    body += get_body_recursive(part)
            else:
                if payload.get('mimeType') == 'text/plain':
                    data = payload.get('body', {}).get('data', '')
                    if data:
                        import base64
                        try:
                            body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        except:
                            pass
            return body

        return get_body_recursive(email.get('payload', {}))

    def _save_corrections(self, session_id: str):
        """Save corrections to file"""
        # Determine appropriate data directory
        data_dirs = ['../data/corrections', 'data/corrections', '.']
        save_dir = '.'

        for data_dir in data_dirs:
            if os.path.exists(data_dir):
                save_dir = data_dir
                break

        filename = os.path.join(save_dir, f"review_corrections_{session_id}.json")
        with open(filename, 'w') as f:
            json.dump(self.corrections_database, f, indent=2)
        print(f"💾 Saved corrections to {filename}")

    def _show_corrections_summary(self, session_id: str):
        """Show summary of corrections made in this session"""
        session_corrections = [c for c in self.corrections_database if c['session_id'] == session_id]

        if not session_corrections:
            print("📝 No corrections found for this session")
            return

        print(f"\n📋 Corrections Summary for Session {session_id}")
        print("=" * 50)

        from collections import Counter
        original_categories = [c['original_category'] for c in session_corrections]
        corrected_categories = [c['corrected_category'] for c in session_corrections]

        print(f"📊 Total corrections: {len(session_corrections)}")
        print(f"\n🔄 Category changes:")

        category_changes = {}
        for correction in session_corrections:
            change = f"{correction['original_category']} → {correction['corrected_category']}"
            category_changes[change] = category_changes.get(change, 0) + 1

        for change, count in sorted(category_changes.items()):
            print(f"   {change} ({count}x)")

        print(f"\n📧 Sample corrections:")
        for i, correction in enumerate(session_corrections[:3]):
            print(f"   {i+1}. From: {correction['email_data']['sender']}")
            print(f"      Subject: {correction['email_data']['subject'][:60]}...")
            print(f"      Changed: {correction['original_category']} → {correction['corrected_category']}")

        if len(session_corrections) > 3:
            print(f"      ... and {len(session_corrections) - 3} more corrections")

    def _export_training_data_summary(self, session_id: str):
        """Export training data and show summary"""
        training_file = self.export_training_data(session_id)
        print(f"\n📄 Training data exported to: {training_file}")
        print("💡 You can use this data later with:")
        print(f"   python gmail_automation.py --retrain-from-corrections {training_file}")

    def _retrain_model_with_corrections(self, session_id: str):
        """Retrain the ML model with the corrections from this session"""
        print(f"\n🔄 Starting model retraining with session {session_id} corrections...")

        if not self.gmail_automation or not hasattr(self.gmail_automation, 'ml_categorizer'):
            print("❌ Gmail automation or ML categorizer not available for retraining")
            self._export_training_data_summary(session_id)
            return

        try:
            # Export training data first
            training_file = self.export_training_data(session_id)

            # Get ML categorizer
            ml_categorizer = self.gmail_automation.ml_categorizer
            if not ml_categorizer:
                print("❌ ML categorizer not initialized")
                self._export_training_data_summary(session_id)
                return

            # Load the training data
            with open(training_file, 'r') as f:
                training_data = json.load(f)

            print(f"📊 Loaded {len(training_data)} corrected examples for retraining")

            # Retrain the model
            print("🧠 Retraining ML model... This may take a few minutes")
            report = ml_categorizer.train_classifier(training_data)

            print(f"\n✅ Model retraining completed!")
            print(f"📈 New model accuracy: {report.get('accuracy', 'N/A'):.3f}")

            # Show improvement metrics if available
            if 'classification_report' in report:
                print(f"📊 Classification improvements:")
                print(f"   • Precision: {report.get('precision', 'N/A')}")
                print(f"   • Recall: {report.get('recall', 'N/A')}")
                print(f"   • F1-Score: {report.get('f1_score', 'N/A')}")

            print(f"\n🎯 The model is now smarter and should categorize emails better!")
            print(f"💾 Training data also saved to: {training_file}")

        except Exception as e:
            print(f"❌ Error during retraining: {e}")
            print("💾 Corrections saved for manual retraining later")
            self._export_training_data_summary(session_id)
            import traceback
            traceback.print_exc()

def main():
    """Example usage of the clustering reviewer"""
    print("🎯 Email Clustering Reviewer - Semi-Supervised Learning")
    print("This tool helps improve email categorization through human feedback")

    # This would normally be integrated with the main Gmail automation
    reviewer = EmailClusteringReviewer()

    print("\n💡 Next steps:")
    print("1. Integrate with gmail_automation.py")
    print("2. Run: python gmail_automation.py --review-clusters")
    print("3. Follow interactive prompts to correct categorizations")
    print("4. Use corrections for model retraining")

if __name__ == "__main__":
    main()