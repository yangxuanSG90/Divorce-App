"""
Module for LLM integration to answer questions based on judgments.
"""

import os
from typing import List, Dict, Optional
import json


class LLMHelper:
    """Helper class for LLM interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM helper.
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.use_openai = self.api_key is not None
        
        # Try to import OpenAI
        try:
            import openai
            self.openai = openai
            if self.api_key:
                # Support both old and new OpenAI API versions
                if hasattr(openai, 'api_key'):
                    openai.api_key = self.api_key
                elif hasattr(openai, 'OpenAI'):
                    self.client = openai.OpenAI(api_key=self.api_key)
                else:
                    self.use_openai = False
        except ImportError:
            self.use_openai = False
    
    def generate_answer(self, question: str, relevant_cases: List[Dict], 
                       use_simple_fallback: bool = True, user_profile: Optional[Dict] = None) -> Dict:
        """
        Generate an answer to a question based on relevant cases.
        
        Args:
            question: User's question
            relevant_cases: List of relevant case dictionaries
            use_simple_fallback: If True, use simple text-based answer if LLM unavailable
            user_profile: Optional user profile dictionary for personalized answers
            
        Returns:
            Dictionary with 'answer', 'case_references', and 'confidence'
        """
        if not relevant_cases:
            return {
                'answer': 'I could not find any relevant cases to answer your question.',
                'case_references': [],
                'confidence': 0.0
            }
        
        # Prepare context from relevant cases
        context_parts = []
        case_references = []
        
        for i, case in enumerate(relevant_cases[:3]):  # Use top 3 cases
            case_info = {
                'case_id': case.get('case_id', ''),
                'filename': case.get('filename', ''),
                'court_level': case.get('court_level', ''),
                'judge_name': case.get('judge_name', ''),
                'judgment_date': case.get('judgment_date', ''),
                'topics': case.get('topic_tags', ''),
                'contested': case.get('contested', False),
                'outcome_summary': self._extract_outcome_summary(case)
            }
            case_references.append(case_info)
            
            # Extract relevant content (first 1500 chars)
            content = case.get('content', '')
            relevant_content = content[:1500] if len(content) > 1500 else content
            
            context_parts.append(f"""
Case {i+1}: {case.get('filename', 'Unknown')}
Court: {case.get('court_level', 'Unknown')}
Judge: {case.get('judge_name', 'Unknown')}
Date: {case.get('judgment_date', 'Unknown')}
Topics: {case.get('topic_tags', 'N/A')}
Contested: {case.get('contested', False)}
Relevant Content:
{relevant_content}
---
""")
        
        context = '\n'.join(context_parts)
        
        if self.use_openai:
            return self._generate_with_openai(question, context, case_references)
        elif use_simple_fallback:
            return self._generate_simple_answer(question, context, case_references)
        else:
            return {
                'answer': 'LLM service is not available. Please set OPENAI_API_KEY environment variable.',
                'case_references': case_references,
                'confidence': 0.5
            }
    
    def _generate_with_openai(self, question: str, context: str, case_references: List[Dict]) -> Dict:
        """Generate answer using OpenAI API."""
        try:
            prompt = f"""You are a legal research assistant specializing in Singapore family law and divorce cases. 
Based on the following judgment excerpts, answer the user's question.

Context from relevant judgments:
{context}

User Question: {question}

Provide a clear, concise answer based on the judgments provided. Include:
1. A direct answer to the question
2. Key legal principles or patterns observed
3. Relevant case outcomes

Answer:"""

            # Try new API first (OpenAI v1.0+)
            if hasattr(self, 'client'):
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful legal research assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
                answer = response.choices[0].message.content.strip()
            # Fallback to old API
            elif hasattr(self.openai, 'ChatCompletion'):
                response = self.openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful legal research assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
                answer = response.choices[0].message.content.strip()
            else:
                raise Exception("OpenAI API not properly configured")
            
            return {
                'answer': answer,
                'case_references': case_references,
                'confidence': 0.8
            }
        except Exception as e:
            return {
                'answer': f'Error generating answer: {str(e)}. Using fallback method.',
                'case_references': case_references,
                'confidence': 0.5
            }
    
    def _generate_simple_answer(self, question: str, context: str, case_references: List[Dict]) -> Dict:
        """Generate a simple text-based answer when LLM is not available."""
        # Extract key information from context
        question_lower = question.lower()
        
        # Simple pattern matching
        if 'outcome' in question_lower or 'result' in question_lower:
            answer = "Based on the relevant cases:\n\n"
            for i, case in enumerate(case_references, 1):
                answer += f"Case {i} ({case.get('filename', 'Unknown')}): "
                answer += f"{case.get('outcome_summary', 'See judgment for details')}\n\n"
        elif 'custody' in question_lower or 'child' in question_lower:
            answer = "The relevant cases involve child custody matters. "
            answer += "Key considerations typically include the child's welfare, "
            answer += "parental capabilities, and the child's best interests. "
            answer += "Please review the specific cases for detailed outcomes."
        elif 'maintenance' in question_lower or 'financial' in question_lower:
            answer = "The relevant cases involve financial matters including maintenance and asset division. "
            answer += "Outcomes depend on factors such as each party's financial means, "
            answer += "marriage duration, and contributions to the marriage."
        elif 'adultery' in question_lower:
            answer = "Some of the relevant cases involve adultery. "
            answer += "Adultery can be a ground for divorce and may affect ancillary matters. "
            answer += "Please review the specific cases for how it was handled."
        else:
            answer = "Based on the relevant cases found, I can provide the following insights:\n\n"
            for i, case in enumerate(case_references, 1):
                answer += f"• {case.get('filename', 'Unknown')} - {case.get('court_level', 'Unknown')} "
                answer += f"({case.get('judgment_date', 'Unknown')})\n"
                answer += f"  Topics: {case.get('topics', 'N/A')}\n\n"
        
        answer += "\n\nNote: This is a simplified answer. For detailed legal analysis, please review the full judgments."
        
        return {
            'answer': answer,
            'case_references': case_references,
            'confidence': 0.6
        }
    
    def _extract_outcome_summary(self, case: Dict) -> str:
        """Extract a brief outcome summary from case data."""
        summary_parts = []
        
        if case.get('contested'):
            summary_parts.append("Contested case")
        else:
            summary_parts.append("Uncontested case")
        
        topics = str(case.get('topic_tags', ''))
        if 'custody' in topics.lower():
            summary_parts.append("involved child custody")
        if 'maintenance' in topics.lower() or 'financial' in topics.lower():
            summary_parts.append("involved financial matters")
        if case.get('mention_of_adultery'):
            summary_parts.append("involved adultery")
        
        asset_bucket = case.get('asset_value_bucket', '')
        if asset_bucket:
            summary_parts.append(f"asset value: {asset_bucket}")
        
        return ", ".join(summary_parts) if summary_parts else "See judgment for details"

