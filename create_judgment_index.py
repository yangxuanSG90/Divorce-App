#!/usr/bin/env python3
"""
Script to create a comprehensive index of judgment MD files with high-value features.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter
import csv

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.tag import pos_tag
    nltk_available = True
except ImportError:
    nltk_available = False
    print("NLTK not available. Some text analysis features will be limited.")


class JudgmentIndexer:
    """Extract high-value features from judgment MD files."""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english')) if nltk_available else set()
        self.sia = SentimentIntensityAnalyzer() if nltk_available else None
        
        # Legal topic keywords
        self.topic_keywords = {
            'child_custody': ['custody', 'care and control', 'children', 'child', 'son', 'daughter', 
                            'parental', 'guardian', 'visitation', 'access'],
            'adultery': ['adultery', 'affair', 'lover', 'infidelity', 'unfaithful', 'cheating', 
                        'extramarital', 'paramour'],
            'cruelty': ['cruelty', 'abuse', 'violence', 'assault', 'harassment', 'threat', 
                       'intimidation', 'cruel', 'abusive'],
            'financials': ['maintenance', 'spousal maintenance', 'alimony', 'assets', 'property', 
                          'division', 'matrimonial assets', 'CPF', 'bank', 'account', 'income', 
                          'salary', 'earnings', 'wealth', 'money', 'financial'],
            'domestic_violence': ['domestic violence', 'DV', 'abuse', 'physical abuse', 
                                 'emotional abuse', 'battered', 'violence', 'assault'],
            'separation': ['separation', 'separate', 'lived apart', 'living apart', 'desertion', 
                          'deserted']
        }
        
        # Legal issue patterns
        self.legal_issue_patterns = [
            r'\$[\d,]+',  # Monetary amounts
            r'[A-Z][a-z]+ v [A-Z][a-z]+',  # Case citations
            r'section \d+',  # Statutory references
            r'\[20\d{2}\]',  # Year citations
        ]
    
    def hash_id(self, text: str) -> str:
        """Create a hashed ID from text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def extract_case_id(self, filename: str, content: str) -> str:
        """Extract and hash case ID from filename or content."""
        # Try to extract from filename (e.g., "vqb-v-vqc-2021-sghcf-5")
        case_match = re.search(r'([a-z]+-v-[a-z]+(?:-and-another-matter)?-\d{4}-[a-z]+-\d+)', filename.lower())
        if case_match:
            return self.hash_id(case_match.group(1))
        
        # Try to extract from content
        case_citation = re.search(r'\[20\d{2}\]\s+[A-Z]+\s+\d+', content)
        if case_citation:
            return self.hash_id(case_citation.group(0))
        
        return self.hash_id(filename)
    
    def extract_dates(self, content: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract filing date and judgment date."""
        filing_date = None
        judgment_date = None
        
        # Look for judgment date (usually at the top)
        date_patterns = [
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in date_patterns:
            dates = re.findall(pattern, content[:2000])  # Check first 2000 chars
            if dates:
                try:
                    judgment_date = dates[0]
                    break
                except:
                    pass
        
        # Look for filing date in text
        filing_patterns = [
            r'filed.*?(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            r'filed.*?(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
            r'filed.*?on\s+(\d{1,2}\s+\w+\s+\d{4})',
        ]
        
        for pattern in filing_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                filing_date = match.group(1)
                break
        
        return filing_date, judgment_date
    
    def extract_court_level(self, filename: str, content: str) -> str:
        """Extract court level from filename or content."""
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        if 'sghcf' in filename_lower or 'family court' in content_lower or 'district judge' in content_lower:
            return 'Family Court'
        elif 'sghc' in filename_lower or 'high court' in content_lower:
            return 'High Court'
        elif 'sgca' in filename_lower or 'court of appeal' in content_lower:
            return 'Court of Appeal'
        else:
            return 'Unknown'
    
    def extract_judge(self, content: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract judge name and create hashed ID."""
        # Look for judge name patterns - more specific patterns first
        judge_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][CJ]?)\s*:',  # "Hoo Sheau Peng JC:"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z])\s*:',  # "Choo Han Teck J:"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][CJ]?)\s*:',  # "Name Name JC:" or "Name Name J:"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)\s*:',  # "Name Name Name:"
        ]
        
        # Also check for patterns after "Judgment reserved" or before judgment text
        content_start = content[:2000]  # Check first 2000 chars
        
        for pattern in judge_patterns:
            match = re.search(pattern, content_start)
            if match:
                judge_name = match.group(1).strip()
                # Filter out false positives like "LawNet Editorial Note"
                if 'editorial' in judge_name.lower() or 'note' in judge_name.lower():
                    continue
                judge_id = self.hash_id(judge_name)
                return judge_name, judge_id
        
        return None, None
    
    def extract_ages(self, content: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract applicant and respondent age ranges."""
        # Look for age patterns
        age_patterns = [
            r'(?:appellant|applicant|wife|husband|petitioner).*?(?:aged|is|was)\s+(\d{1,2})',
            r'(?:respondent|defendant).*?(?:aged|is|was)\s+(\d{1,2})',
            r'(\d{1,2})\s+years?\s+old',
        ]
        
        applicant_age = None
        respondent_age = None
        
        # Try to find ages in context
        age_matches = re.findall(r'(\d{1,2})\s+years?\s+old', content[:3000])
        if len(age_matches) >= 2:
            applicant_age = self._age_to_range(int(age_matches[0]))
            respondent_age = self._age_to_range(int(age_matches[1]))
        elif len(age_matches) == 1:
            applicant_age = self._age_to_range(int(age_matches[0]))
        
        return applicant_age, respondent_age
    
    def _age_to_range(self, age: int) -> str:
        """Convert age to age range."""
        if age < 30:
            return '20-29'
        elif age < 40:
            return '30-39'
        elif age < 50:
            return '40-49'
        elif age < 60:
            return '50-59'
        elif age < 70:
            return '60-69'
        else:
            return '70+'
    
    def count_witnesses(self, content: str) -> int:
        """Count number of witnesses mentioned."""
        witness_patterns = [
            r'witness',
            r'affidavit',
            r'testimony',
            r'deposition',
        ]
        
        count = 0
        for pattern in witness_patterns:
            count += len(re.findall(pattern, content, re.IGNORECASE))
        
        # Rough estimate - divide by 3 to avoid overcounting
        return max(0, count // 3)
    
    def is_contested(self, content: str) -> bool:
        """Determine if hearings were contested."""
        contested_keywords = ['contested', 'defended', 'opposed', 'challenged', 'disputed']
        uncontested_keywords = ['uncontested', 'consent', 'agreed', 'by consent']
        
        content_lower = content.lower()
        contested_count = sum(1 for kw in contested_keywords if kw in content_lower)
        uncontested_count = sum(1 for kw in uncontested_keywords if kw in content_lower)
        
        return contested_count > uncontested_count
    
    def extract_legal_representation(self, content: str) -> str:
        """Determine legal representation status."""
        content_lower = content.lower()
        
        # Look for representation indicators
        has_counsel = bool(re.search(r'counsel|solicitor|lawyer|attorney', content_lower))
        has_appellant_counsel = bool(re.search(r'appellant.*?counsel|appellant.*?solicitor', content_lower))
        has_respondent_counsel = bool(re.search(r'respondent.*?counsel|respondent.*?solicitor', content_lower))
        pro_se = bool(re.search(r'pro se|self-represented|in person', content_lower))
        
        if has_appellant_counsel and has_respondent_counsel:
            return 'both_represented'
        elif has_counsel and not (has_appellant_counsel and has_respondent_counsel):
            return 'one_represented'
        elif pro_se:
            return 'both_pro_se'
        else:
            return 'unknown'
    
    def extract_jurisdictional_tags(self, content: str) -> Dict[str, bool]:
        """Extract jurisdictional tags for ancillary matters."""
        content_lower = content.lower()
        
        return {
            'maintenance': bool(re.search(r'maintenance|spousal maintenance|alimony', content_lower)),
            'custody': bool(re.search(r'custody|care and control|children|child', content_lower)),
            'division_of_assets': bool(re.search(r'division.*?assets|matrimonial assets|property.*?division', content_lower))
        }
    
    def has_prior_cases(self, content: str) -> bool:
        """Check if there are mentions of prior cases between parties."""
        prior_case_patterns = [
            r'previous.*?case',
            r'earlier.*?proceeding',
            r'prior.*?petition',
            r'previous.*?application',
        ]
        
        content_lower = content.lower()
        return any(re.search(pattern, content_lower) for pattern in prior_case_patterns)
    
    def extract_topics(self, content: str) -> List[str]:
        """Extract topic tags from content."""
        content_lower = content.lower()
        topics = []
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def check_mention(self, content: str, keywords: List[str]) -> bool:
        """Check if content mentions specific keywords."""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in keywords)
    
    def extract_child_ages(self, content: str) -> Dict[str, Optional[int]]:
        """Extract child ages mentioned in the judgment."""
        # Look for child age patterns
        age_patterns = [
            r'(?:son|daughter|child).*?(?:aged|age)\s+(\d{1,2})',
            r'(\d{1,2})\s+years?\s+old.*?(?:son|daughter|child)',
            r'(?:son|daughter|child).*?(\d{1,2})\s+years?',
        ]
        
        ages = []
        for pattern in age_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    age = int(match)
                    if 0 <= age <= 18:  # Reasonable child age range
                        ages.append(age)
                except:
                    pass
        
        if not ages:
            return {'min': None, 'max': None, 'median': None}
        
        return {
            'min': min(ages),
            'max': max(ages),
            'median': sorted(ages)[len(ages)//2] if ages else None
        }
    
    def extract_asset_values(self, content: str) -> List[float]:
        """Extract asset values mentioned."""
        # Look for monetary amounts
        amount_patterns = [
            r'\$([\d,]+(?:\.\d{2})?)',
            r'S\$([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:dollars?|SGD)',
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    if amount > 100:  # Filter out small amounts
                        amounts.append(amount)
                except:
                    pass
        
        return amounts
    
    def calculate_days_between(self, filing_date: Optional[str], judgment_date: Optional[str]) -> Optional[int]:
        """Calculate days between filing and judgment."""
        if not filing_date or not judgment_date:
            return None
        
        try:
            # Try to parse dates
            date_formats = [
                '%d %B %Y',
                '%d %b %Y',
                '%Y-%m-%d',
                '%d %B %Y',
            ]
            
            filing_dt = None
            judgment_dt = None
            
            for fmt in date_formats:
                try:
                    filing_dt = datetime.strptime(filing_date, fmt)
                    break
                except:
                    continue
            
            for fmt in date_formats:
                try:
                    judgment_dt = datetime.strptime(judgment_date, fmt)
                    break
                except:
                    continue
            
            if filing_dt and judgment_dt:
                return (judgment_dt - filing_dt).days
        except:
            pass
        
        return None
    
    def count_legal_issues(self, content: str) -> int:
        """Count number of legal issues/transactions disputed."""
        # Look for dispute indicators
        dispute_patterns = [
            r'disputed',
            r'challenged',
            r'contested',
            r'disagreement',
            r'dispute',
        ]
        
        count = 0
        for pattern in dispute_patterns:
            count += len(re.findall(pattern, content, re.IGNORECASE))
        
        return count
    
    def calculate_sentiment(self, content: str) -> Optional[float]:
        """Calculate sentiment score (judge tone)."""
        if not self.sia:
            return None
        
        # Analyze sentiment of key paragraphs
        sentences = sent_tokenize(content[:5000])  # First 5000 chars
        if not sentences:
            return None
        
        scores = []
        for sentence in sentences[:20]:  # Limit to first 20 sentences
            score = self.sia.polarity_scores(sentence)
            scores.append(score['compound'])
        
        return sum(scores) / len(scores) if scores else None
    
    def process_judgment(self, filepath: Path) -> Dict:
        """Process a single judgment file and extract all features."""
        print(f"Processing: {filepath.name}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = filepath.name
        case_id = self.extract_case_id(filename, content)
        filing_date, judgment_date = self.extract_dates(content)
        court_level = self.extract_court_level(filename, content)
        judge_name, judge_id = self.extract_judge(content)
        applicant_age, respondent_age = self.extract_ages(content)
        
        # Structured features
        structured_features = {
            'case_id': case_id,
            'filename': filename,
            'filing_date': filing_date,
            'judgment_date': judgment_date,
            'court_level': court_level,
            'judge_name': judge_name,
            'judge_id': judge_id,
            'applicant_role_age_range': applicant_age,
            'respondent_role_age_range': respondent_age,
            'number_of_witnesses': self.count_witnesses(content),
            'contested': self.is_contested(content),
            'legal_representation': self.extract_legal_representation(content),
        }
        
        # Jurisdictional tags
        jurisdictional_tags = self.extract_jurisdictional_tags(content)
        structured_features.update(jurisdictional_tags)
        structured_features['prior_cases_between_parties'] = self.has_prior_cases(content)
        
        # Text-derived features
        topics = self.extract_topics(content)
        child_ages = self.extract_child_ages(content)
        asset_values = self.extract_asset_values(content)
        
        text_features = {
            'topic_tags': topics,
            'mention_of_domestic_violence': self.check_mention(content, 
                self.topic_keywords['domestic_violence']),
            'mention_of_adultery': self.check_mention(content, 
                self.topic_keywords['adultery']),
            'legal_issue_counts': self.count_legal_issues(content),
            'sentiment_score': self.calculate_sentiment(content),
        }
        
        # Derived aggregated features
        days_between = self.calculate_days_between(filing_date, judgment_date)
        
        asset_value_bucket = None
        if asset_values:
            total_assets = sum(asset_values)
            if total_assets < 100000:
                asset_value_bucket = '<100k'
            elif total_assets < 500000:
                asset_value_bucket = '100k-500k'
            elif total_assets < 1000000:
                asset_value_bucket = '500k-1M'
            else:
                asset_value_bucket = '>1M'
        
        derived_features = {
            'days_between_filing_and_judgment': days_between,
            'child_ages_present': child_ages,
            'asset_value_bucket': asset_value_bucket,
        }
        
        # Combine all features
        result = {
            **structured_features,
            **text_features,
            **derived_features,
        }
        
        return result


def main():
    """Main function to process all judgment files."""
    # Download NLTK data if needed
    if nltk_available:
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            print("Downloading NLTK punkt_tab tokenizer...")
            nltk.download('punkt_tab', quiet=True)
        
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            print("Downloading NLTK VADER lexicon...")
            nltk.download('vader_lexicon', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            print("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True)
    
    script_dir = Path(__file__).parent
    pdf_dir = script_dir / "Sample PDFs"
    
    if not pdf_dir.exists():
        print(f"Error: Directory '{pdf_dir}' does not exist.")
        return
    
    md_files = list(pdf_dir.glob("*.md"))
    
    if not md_files:
        print(f"No MD files found in '{pdf_dir}'")
        return
    
    print(f"Found {len(md_files)} MD file(s) to index...\n")
    
    indexer = JudgmentIndexer()
    index_data = []
    
    for md_file in sorted(md_files):
        try:
            features = indexer.process_judgment(md_file)
            index_data.append(features)
            print(f"  ✓ Indexed: {md_file.name}\n")
        except Exception as e:
            print(f"  ✗ Error indexing {md_file.name}: {str(e)}\n")
    
    # Save as JSON
    json_path = script_dir / "judgment_index.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON index to: {json_path}")
    
    # Save as CSV
    csv_path = script_dir / "judgment_index.csv"
    if index_data:
        # Flatten nested structures for CSV
        csv_rows = []
        for item in index_data:
            row = item.copy()
            # Flatten topic_tags
            row['topic_tags'] = ', '.join(row.get('topic_tags', []))
            # Flatten child_ages
            child_ages = row.get('child_ages_present', {})
            row['child_age_min'] = child_ages.get('min')
            row['child_age_max'] = child_ages.get('max')
            row['child_age_median'] = child_ages.get('median')
            del row['child_ages_present']
            csv_rows.append(row)
        
        fieldnames = csv_rows[0].keys()
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"Saved CSV index to: {csv_path}")
    
    print(f"\nIndexing complete! Processed {len(index_data)} judgment(s).")


if __name__ == "__main__":
    main()

