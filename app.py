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

# Initialize user profile in session state
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'applicant_age_range': None,
        'respondent_age_range': None,
        'contested': None,
        'maintenance': False,
        'custody': False,
        'division_of_assets': False,
        'mention_of_adultery': False,
        'mention_of_domestic_violence': False,
        'separation': False,
        'asset_value_bucket': None,
        'child_age_min': None,
        'child_age_max': None,
        'legal_representation': None,
        'court_level': None,
        'prior_cases': False
    }

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
tab1, tab2, tab3 = st.tabs(["💬 Ask Question", "👤 My Profile", "📚 Browse Cases"])

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
    
    # Show profile status
    profile = st.session_state.user_profile
    profile_filled = any(v not in [None, False, ""] for v in profile.values())
    
    if profile_filled:
        st.info("ℹ️ Your profile is being used to find more relevant cases. Update it in the 'My Profile' tab.")
    
    if ask_button and question:
        with st.spinner("Searching relevant cases and generating answer..."):
            # Search for relevant cases - use profile if available
            keywords = question.split()
            
            # If profile is filled, use feature-based search first
            if profile_filled:
                # Build search features from profile
                search_features = {}
                
                if profile.get('contested') is not None:
                    search_features['contested'] = profile['contested']
                if profile.get('maintenance'):
                    search_features['maintenance'] = True
                if profile.get('custody'):
                    search_features['custody'] = True
                if profile.get('division_of_assets'):
                    search_features['division_of_assets'] = True
                if profile.get('mention_of_adultery'):
                    search_features['mention_of_adultery'] = True
                if profile.get('mention_of_domestic_violence'):
                    search_features['mention_of_domestic_violence'] = True
                if profile.get('court_level'):
                    search_features['court_level'] = profile['court_level']
                
                # Search by features
                feature_cases = loader.search_by_features(search_features, max_results=5)
                
                # Also do keyword search
                keyword_cases = loader.search_by_keywords(keywords, max_results=5)
                
                # Combine and deduplicate (prefer feature matches)
                relevant_cases = feature_cases
                seen_ids = {c.get('case_id') for c in relevant_cases}
                for case in keyword_cases:
                    if case.get('case_id') not in seen_ids:
                        relevant_cases.append(case)
                        seen_ids.add(case.get('case_id'))
                
                relevant_cases = relevant_cases[:5]  # Limit to 5
            else:
                # Just keyword search
                relevant_cases = loader.search_by_keywords(keywords, max_results=5)
            
            if not relevant_cases:
                st.warning("No relevant cases found. Try rephrasing your question.")
            else:
                # Generate answer with profile context
                llm_helper = st.session_state.llm_helper
                
                # Add profile context to question if profile is filled
                enhanced_question = question
                if profile_filled:
                    profile_context = "User's situation: "
                    profile_parts = []
                    
                    if profile.get('applicant_age_range'):
                        profile_parts.append(f"Age: {profile['applicant_age_range']}")
                    if profile.get('contested') is not None:
                        profile_parts.append(f"Contested: {'Yes' if profile['contested'] else 'No'}")
                    if profile.get('custody'):
                        profile_parts.append("Child custody issues")
                    if profile.get('maintenance'):
                        profile_parts.append("Maintenance issues")
                    if profile.get('division_of_assets'):
                        profile_parts.append("Asset division")
                    if profile.get('mention_of_adultery'):
                        profile_parts.append("Adultery involved")
                    if profile.get('mention_of_domestic_violence'):
                        profile_parts.append("Domestic violence")
                    if profile.get('asset_value_bucket'):
                        profile_parts.append(f"Assets: {profile['asset_value_bucket']}")
                    if profile.get('child_age_min') is not None:
                        profile_parts.append(f"Children ages: {profile['child_age_min']}-{profile['child_age_max']} years")
                    
                    if profile_parts:
                        profile_context += ", ".join(profile_parts)
                        enhanced_question = f"{question}\n\n{profile_context}"
                
                result = llm_helper.generate_answer(enhanced_question, relevant_cases, user_profile=profile if profile_filled else None)
                
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
    st.header("👤 My Profile")
    st.markdown("""
    Fill in your situation details to help the system find more relevant cases and provide personalized insights.
    All information is stored locally and not shared.
    """)
    
    profile = st.session_state.user_profile
    
    # Personal Information
    st.subheader("Personal Information")
    col1, col2 = st.columns(2)
    
    with col1:
        age_ranges = [None, "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
        profile['applicant_age_range'] = st.selectbox(
            "Your Age Range",
            age_ranges,
            index=age_ranges.index(profile['applicant_age_range']) if profile['applicant_age_range'] in age_ranges else 0,
            help="Select your age range"
        )
    
    with col2:
        profile['respondent_age_range'] = st.selectbox(
            "Spouse's Age Range",
            age_ranges,
            index=age_ranges.index(profile['respondent_age_range']) if profile['respondent_age_range'] in age_ranges else 0,
            help="Select your spouse's age range"
        )
    
    # Case Details
    st.subheader("Case Details")
    
    profile['contested'] = st.radio(
        "Is your case contested?",
        [None, True, False],
        format_func=lambda x: "Not specified" if x is None else ("Yes" if x else "No"),
        index=[None, True, False].index(profile['contested']) if profile['contested'] in [None, True, False] else 0,
        horizontal=True
    )
    
    profile['legal_representation'] = st.selectbox(
        "Legal Representation",
        [None, "both_represented", "one_represented", "both_pro_se"],
        format_func=lambda x: {
            None: "Not specified",
            "both_represented": "Both parties have lawyers",
            "one_represented": "One party has a lawyer",
            "both_pro_se": "Both parties self-represented"
        }.get(x, x),
        index=[None, "both_represented", "one_represented", "both_pro_se"].index(profile['legal_representation']) if profile['legal_representation'] in [None, "both_represented", "one_represented", "both_pro_se"] else 0
    )
    
    profile['court_level'] = st.selectbox(
        "Court Level",
        [None, "Family Court", "High Court", "Court of Appeal"],
        index=[None, "Family Court", "High Court", "Court of Appeal"].index(profile['court_level']) if profile['court_level'] in [None, "Family Court", "High Court", "Court of Appeal"] else 0
    )
    
    # Issues/Topics
    st.subheader("Issues in Your Case")
    st.markdown("Select all that apply:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        profile['custody'] = st.checkbox("Child Custody", value=profile['custody'])
        profile['maintenance'] = st.checkbox("Maintenance/Spousal Support", value=profile['maintenance'])
    
    with col2:
        profile['division_of_assets'] = st.checkbox("Division of Assets", value=profile['division_of_assets'])
        profile['separation'] = st.checkbox("Separation Issues", value=profile['separation'])
    
    with col3:
        profile['mention_of_adultery'] = st.checkbox("Adultery", value=profile['mention_of_adultery'])
        profile['mention_of_domestic_violence'] = st.checkbox("Domestic Violence", value=profile['mention_of_domestic_violence'])
    
    profile['prior_cases'] = st.checkbox("Prior cases between parties", value=profile['prior_cases'])
    
    # Financial Information
    st.subheader("Financial Information")
    
    profile['asset_value_bucket'] = st.selectbox(
        "Estimated Asset Value",
        [None, "<100k", "100k-500k", "500k-1M", ">1M"],
        index=[None, "<100k", "100k-500k", "500k-1M", ">1M"].index(profile['asset_value_bucket']) if profile['asset_value_bucket'] in [None, "<100k", "100k-500k", "500k-1M", ">1M"] else 0,
        help="Estimated total value of matrimonial assets"
    )
    
    # Child Information
    st.subheader("Child Information (if applicable)")
    
    has_children = st.checkbox("I have children", value=profile['child_age_min'] is not None or profile['child_age_max'] is not None)
    
    if has_children:
        col1, col2 = st.columns(2)
        with col1:
            profile['child_age_min'] = st.number_input(
                "Youngest Child Age",
                min_value=0,
                max_value=18,
                value=int(profile['child_age_min']) if profile['child_age_min'] is not None else 0,
                step=1
            )
        with col2:
            profile['child_age_max'] = st.number_input(
                "Oldest Child Age",
                min_value=0,
                max_value=18,
                value=int(profile['child_age_max']) if profile['child_age_max'] is not None else 0,
                step=1
            )
    else:
        profile['child_age_min'] = None
        profile['child_age_max'] = None
    
    # Save and Clear buttons
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Profile", use_container_width=True):
            st.session_state.user_profile = profile
            st.success("Profile saved!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Profile", use_container_width=True):
            st.session_state.user_profile = {
                'applicant_age_range': None,
                'respondent_age_range': None,
                'contested': None,
                'maintenance': False,
                'custody': False,
                'division_of_assets': False,
                'mention_of_adultery': False,
                'mention_of_domestic_violence': False,
                'separation': False,
                'asset_value_bucket': None,
                'child_age_min': None,
                'child_age_max': None,
                'legal_representation': None,
                'court_level': None,
                'prior_cases': False
            }
            st.success("Profile cleared!")
            st.rerun()
    
    # Display current profile summary
    st.divider()
    st.subheader("Profile Summary")
    
    filled_fields = sum(1 for k, v in profile.items() if v not in [None, False, ""])
    total_fields = len([k for k in profile.keys() if k != 'child_age_median'])
    
    if filled_fields > 0:
        st.progress(filled_fields / total_fields)
        st.caption(f"Profile completeness: {filled_fields}/{total_fields} fields filled")
        
        # Show filled fields
        with st.expander("View Profile Details"):
            for key, value in profile.items():
                if value not in [None, False, ""]:
                    display_key = key.replace('_', ' ').title()
                    if isinstance(value, bool):
                        display_value = "Yes" if value else "No"
                    else:
                        display_value = str(value)
                    st.write(f"**{display_key}:** {display_value}")
    else:
        st.info("Fill in your profile to get personalized case recommendations and insights.")
    
    # Show similar cases based on profile
    if profile_filled:
        st.divider()
        st.subheader("🔍 Similar Cases Based on Your Profile")
        
        if st.button("Find Similar Cases", type="primary"):
            with st.spinner("Searching for similar cases..."):
                # Build search features from profile
                search_features = {}
                
                if profile.get('contested') is not None:
                    search_features['contested'] = profile['contested']
                if profile.get('maintenance'):
                    search_features['maintenance'] = True
                if profile.get('custody'):
                    search_features['custody'] = True
                if profile.get('division_of_assets'):
                    search_features['division_of_assets'] = True
                if profile.get('mention_of_adultery'):
                    search_features['mention_of_adultery'] = True
                if profile.get('mention_of_domestic_violence'):
                    search_features['mention_of_domestic_violence'] = True
                if profile.get('court_level'):
                    search_features['court_level'] = profile['court_level']
                
                similar_cases = loader.search_by_features(search_features, max_results=5)
                
                if similar_cases:
                    st.success(f"Found {len(similar_cases)} similar case(s)")
                    
                    for i, case in enumerate(similar_cases, 1):
                        with st.expander(f"Case {i}: {case.get('filename', 'Unknown')}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Court:**", case.get('court_level', 'N/A'))
                                st.write("**Judge:**", case.get('judge_name', 'N/A'))
                                st.write("**Date:**", case.get('judgment_date', 'N/A'))
                            
                            with col2:
                                st.write("**Topics:**", case.get('topic_tags', 'N/A'))
                                st.write("**Contested:**", "Yes" if case.get('contested') else "No")
                                st.write("**Asset Value:**", case.get('asset_value_bucket', 'N/A') or 'N/A')
                            
                            if case.get('child_age_min') is not None:
                                st.write("**Child Ages:**", f"{case.get('child_age_min')}-{case.get('child_age_max')} years")
                else:
                    st.warning("No similar cases found. Try adjusting your profile criteria.")

with tab3:
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

