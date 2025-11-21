"""
Streamlit app for querying divorce judgment database.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.judgment_loader import JudgmentLoader
from app.llm_helper import LLMHelper

# Page configuration
st.set_page_config(
    page_title="Divorce Judgment Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'loader' not in st.session_state:
    # Get paths relative to app directory
    app_dir = Path(__file__).parent.parent
    index_path = app_dir / "judgment_index.csv"
    judgments_dir = app_dir / "Sample PDFs"
    
    try:
        st.session_state.loader = JudgmentLoader(str(index_path), str(judgments_dir))
        st.session_state.llm_helper = LLMHelper()
    except Exception as e:
        st.error(f"Error loading judgments: {str(e)}")
        st.stop()

# Title and description
st.title("⚖️ Divorce Judgment Analyzer")
st.markdown("""
Ask questions about divorce cases and get insights based on past judgments.
The system analyzes the judgment database to provide relevant case references and outcomes.
""")

# Sidebar
with st.sidebar:
    st.header("📊 Database Statistics")
    loader = st.session_state.loader
    
    if loader.index_df is not None:
        total_cases = len(loader.index_df)
        st.metric("Total Cases", total_cases)
        
        contested = loader.index_df['contested'].sum() if 'contested' in loader.index_df.columns else 0
        st.metric("Contested Cases", contested)
        
        with_adultery = loader.index_df['mention_of_adultery'].sum() if 'mention_of_adultery' in loader.index_df.columns else 0
        st.metric("Cases with Adultery", with_adultery)
        
        with_dv = loader.index_df['mention_of_domestic_violence'].sum() if 'mention_of_domestic_violence' in loader.index_df.columns else 0
        st.metric("Cases with Domestic Violence", with_dv)
    
    st.divider()
    st.header("🔍 Search Options")
    search_mode = st.radio(
        "Search Mode",
        ["Keyword Search", "Feature Filter"],
        help="Choose how to search for relevant cases"
    )

# Main content area
tab1, tab2 = st.tabs(["💬 Ask Question", "📚 Browse Cases"])

with tab1:
    st.header("Ask a Question")
    
    # Question input
    question = st.text_area(
        "Enter your question:",
        placeholder="e.g., What are the typical outcomes for cases involving adultery and child custody?",
        height=100
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        ask_button = st.button("🔍 Search & Analyze", type="primary", use_container_width=True)
    
    if ask_button and question:
        with st.spinner("Searching relevant cases and generating answer..."):
            # Search for relevant cases
            keywords = question.split()
            relevant_cases = loader.search_by_keywords(keywords, max_results=5)
            
            if not relevant_cases:
                st.warning("No relevant cases found. Try rephrasing your question.")
            else:
                # Generate answer
                llm_helper = st.session_state.llm_helper
                result = llm_helper.generate_answer(question, relevant_cases)
                
                # Display answer
                st.subheader("📝 Answer")
                st.markdown(result['answer'])
                
                # Display confidence
                confidence = result.get('confidence', 0.0)
                st.caption(f"Confidence: {confidence:.0%}")
                
                # Display case references
                st.subheader("📋 Relevant Case References")
                
                for i, case_ref in enumerate(result['case_references'], 1):
                    with st.expander(f"Case {i}: {case_ref.get('filename', 'Unknown')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Court:**", case_ref.get('court_level', 'N/A'))
                            st.write("**Judge:**", case_ref.get('judge_name', 'N/A'))
                            st.write("**Date:**", case_ref.get('judgment_date', 'N/A'))
                        
                        with col2:
                            st.write("**Topics:**", case_ref.get('topics', 'N/A'))
                            st.write("**Contested:**", "Yes" if case_ref.get('contested') else "No")
                        
                        st.write("**Outcome Summary:**", case_ref.get('outcome_summary', 'N/A'))
                        
                        # Show relevant excerpt
                        case_id = case_ref.get('case_id', '')
                        if case_id:
                            case_data = loader.get_case_by_id(case_id)
                            if case_data:
                                excerpt = loader.extract_relevant_sections(
                                    case_data.get('content', ''),
                                    question,
                                    max_chars=1000
                                )
                                st.markdown("**Relevant Excerpt:**")
                                st.text_area(
                                    "",
                                    excerpt,
                                    height=200,
                                    key=f"excerpt_{i}",
                                    label_visibility="collapsed"
                                )
    
    elif ask_button:
        st.warning("Please enter a question first.")

with tab2:
    st.header("Browse All Cases")
    
    # Display all cases in a table
    if loader.index_df is not None:
        # Create a simplified view
        display_df = loader.index_df[[
            'filename', 'court_level', 'judge_name', 'judgment_date',
            'contested', 'topic_tags', 'mention_of_adultery', 'mention_of_domestic_violence'
        ]].copy()
        
        # Rename columns for better display
        display_df.columns = [
            'Case File', 'Court', 'Judge', 'Date',
            'Contested', 'Topics', 'Adultery', 'Domestic Violence'
        ]
        
        # Format boolean columns
        display_df['Contested'] = display_df['Contested'].map({True: 'Yes', False: 'No'})
        display_df['Adultery'] = display_df['Adultery'].map({True: 'Yes', False: 'No'})
        display_df['Domestic Violence'] = display_df['Domestic Violence'].map({True: 'Yes', False: 'No'})
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Allow user to select a case for detailed view
        st.subheader("View Case Details")
        case_files = display_df['Case File'].tolist()
        selected_case = st.selectbox("Select a case to view details:", case_files)
        
        if selected_case:
            case_row = loader.index_df[loader.index_df['filename'] == selected_case]
            if not case_row.empty:
                case_id = case_row.iloc[0]['case_id']
                case_data = loader.get_case_by_id(case_id)
                
                if case_data:
                    st.subheader(f"Case: {selected_case}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Court Level", case_data.get('court_level', 'N/A'))
                        st.metric("Judge", case_data.get('judge_name', 'N/A'))
                    with col2:
                        st.metric("Filing Date", case_data.get('filing_date', 'N/A') or 'N/A')
                        st.metric("Judgment Date", case_data.get('judgment_date', 'N/A'))
                    with col3:
                        st.metric("Contested", "Yes" if case_data.get('contested') else "No")
                        st.metric("Asset Value", case_data.get('asset_value_bucket', 'N/A') or 'N/A')
                    
                    st.write("**Topics:**", case_data.get('topic_tags', 'N/A'))
                    st.write("**Legal Representation:**", case_data.get('legal_representation', 'N/A'))
                    
                    # Show full judgment content
                    with st.expander("View Full Judgment Content"):
                        st.text_area(
                            "",
                            case_data.get('content', ''),
                            height=400,
                            label_visibility="collapsed"
                        )

# Footer
st.divider()
st.caption("""
**Note:** This tool provides insights based on past judgments for reference purposes only. 
It does not constitute legal advice. Please consult with a qualified legal professional for specific legal matters.
""")

