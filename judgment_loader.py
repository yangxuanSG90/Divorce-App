"""
Module for loading and managing judgment data.
"""

import pandas as pd
import os
from pathlib import Path
from typing import List, Dict, Optional
import re


class JudgmentLoader:
    """Load and manage judgment index and content."""
    
    def __init__(self, index_path: str, judgments_dir: str):
        """
        Initialize the judgment loader.
        
        Args:
            index_path: Path to the judgment_index.csv file
            judgments_dir: Directory containing the MD judgment files
        """
        self.index_path = Path(index_path)
        self.judgments_dir = Path(judgments_dir)
        self.index_df = None
        self.judgments = {}  # case_id -> content
        
        self._load_index()
        self._load_judgments()
    
    def _load_index(self):
        """Load the judgment index CSV."""
        if self.index_path.exists():
            self.index_df = pd.read_csv(self.index_path)
            # Convert boolean strings to actual booleans
            bool_cols = ['contested', 'maintenance', 'custody', 'division_of_assets', 
                         'prior_cases_between_parties', 'mention_of_domestic_violence', 
                         'mention_of_adultery']
            for col in bool_cols:
                if col in self.index_df.columns:
                    self.index_df[col] = self.index_df[col].astype(bool)
        else:
            raise FileNotFoundError(f"Index file not found: {self.index_path}")
    
    def _load_judgments(self):
        """Load all judgment MD files."""
        if not self.judgments_dir.exists():
            raise FileNotFoundError(f"Judgments directory not found: {self.judgments_dir}")
        
        for _, row in self.index_df.iterrows():
            filename = row['filename']
            case_id = row['case_id']
            filepath = self.judgments_dir / filename
            
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.judgments[case_id] = f.read()
    
    def search_by_keywords(self, keywords: List[str], max_results: int = 5) -> List[Dict]:
        """
        Search judgments by keywords.
        
        Args:
            keywords: List of keywords to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of matching case dictionaries
        """
        if not keywords:
            return []
        
        results = []
        keywords_lower = [kw.lower() for kw in keywords]
        
        for _, row in self.index_df.iterrows():
            case_id = row['case_id']
            content = self.judgments.get(case_id, '')
            content_lower = content.lower()
            
            # Score based on keyword matches
            score = sum(1 for kw in keywords_lower if kw in content_lower)
            
            # Also check topic tags
            topic_tags = str(row.get('topic_tags', '')).lower()
            topic_score = sum(1 for kw in keywords_lower if kw in topic_tags)
            
            total_score = score + (topic_score * 2)  # Weight topic tags higher
            
            if total_score > 0:
                case_dict = row.to_dict()
                case_dict['relevance_score'] = total_score
                case_dict['content'] = content
                results.append(case_dict)
        
        # Sort by relevance score
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:max_results]
    
    def search_by_features(self, features: Dict, max_results: int = 5) -> List[Dict]:
        """
        Search judgments by structured features.
        
        Args:
            features: Dictionary of features to match (e.g., {'contested': True, 'mention_of_adultery': True})
            max_results: Maximum number of results to return
            
        Returns:
            List of matching case dictionaries
        """
        if not features:
            return []
        
        # Filter dataframe by features
        filtered_df = self.index_df.copy()
        
        for key, value in features.items():
            if key in filtered_df.columns:
                if isinstance(value, bool):
                    filtered_df = filtered_df[filtered_df[key] == value]
                elif isinstance(value, list):
                    # For topic tags, check if any tag in the list matches
                    if key == 'topic_tags':
                        mask = filtered_df[key].str.contains('|'.join(value), case=False, na=False)
                        filtered_df = filtered_df[mask]
                else:
                    filtered_df = filtered_df[filtered_df[key] == value]
        
        results = []
        for _, row in filtered_df.iterrows():
            case_id = row['case_id']
            case_dict = row.to_dict()
            case_dict['content'] = self.judgments.get(case_id, '')
            results.append(case_dict)
        
        return results[:max_results]
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        """Get a specific case by its ID."""
        row = self.index_df[self.index_df['case_id'] == case_id]
        if row.empty:
            return None
        
        case_dict = row.iloc[0].to_dict()
        case_dict['content'] = self.judgments.get(case_id, '')
        return case_dict
    
    def get_all_cases(self) -> List[Dict]:
        """Get all cases."""
        results = []
        for _, row in self.index_df.iterrows():
            case_id = row['case_id']
            case_dict = row.to_dict()
            case_dict['content'] = self.judgments.get(case_id, '')
            results.append(case_dict)
        return results
    
    def extract_relevant_sections(self, content: str, query: str, max_chars: int = 2000) -> str:
        """
        Extract relevant sections from judgment content based on query.
        
        Args:
            content: Full judgment content
            query: Search query
            max_chars: Maximum characters to return
            
        Returns:
            Relevant excerpt from the judgment
        """
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Split into paragraphs
        paragraphs = content.split('\n\n')
        
        # Score paragraphs by keyword matches
        scored_paragraphs = []
        query_words = set(query_lower.split())
        
        for para in paragraphs:
            if len(para.strip()) < 50:  # Skip very short paragraphs
                continue
            
            para_lower = para.lower()
            # Count matching words
            matches = sum(1 for word in query_words if word in para_lower)
            if matches > 0:
                scored_paragraphs.append((matches, para))
        
        # Sort by score and take top paragraphs
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
        
        # Combine top paragraphs
        relevant_text = ''
        for _, para in scored_paragraphs[:5]:  # Top 5 paragraphs
            if len(relevant_text) + len(para) < max_chars:
                relevant_text += para + '\n\n'
            else:
                break
        
        # If we don't have enough, take the beginning
        if len(relevant_text) < 500:
            relevant_text = content[:max_chars]
        
        return relevant_text.strip()

