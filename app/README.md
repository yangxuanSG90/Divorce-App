# Divorce Judgment Analyzer App

A Streamlit web application that allows users to query a database of divorce judgments and get AI-powered answers based on past case analysis.

## Features

- **Question Answering**: Ask questions about divorce cases and get answers based on relevant past judgments
- **Case Search**: Find relevant cases using keyword search or feature filters
- **Case References**: View detailed information about relevant cases including:
  - Court level and judge information
  - Case topics and outcomes
  - Relevant excerpts from judgments
- **Case Browser**: Browse all cases in the database with detailed views

## Setup

### Prerequisites

- Python 3.9 or higher
- Access to the judgment index CSV and MD files

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Set up OpenAI API key for enhanced LLM responses:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

If you don't set the API key, the app will use a simple text-based fallback method.

### Running the App

From the app directory:
```bash
streamlit run app.py
```

Or from the parent directory:
```bash
streamlit run app/app.py
```

The app will open in your default web browser at `http://localhost:8501`.

## Usage

### Asking Questions

1. Go to the "Ask Question" tab
2. Enter your question in the text area (e.g., "What are typical outcomes for cases involving adultery?")
3. Click "Search & Analyze"
4. Review the answer and relevant case references

### Browsing Cases

1. Go to the "Browse Cases" tab
2. View the table of all cases
3. Select a case from the dropdown to see detailed information
4. Expand "View Full Judgment Content" to read the complete judgment

## Architecture

### Components

- **`app.py`**: Main Streamlit application
- **`judgment_loader.py`**: Handles loading and searching judgment data
- **`llm_helper.py`**: Manages LLM integration for generating answers

### Data Flow

1. User enters a question
2. System searches for relevant cases using keyword matching
3. Relevant case excerpts are extracted
4. LLM (or fallback) generates an answer based on the cases
5. Results are displayed with case references

## Configuration

### Using OpenAI API

For best results, set your OpenAI API key:
- Environment variable: `OPENAI_API_KEY`
- Or modify `llm_helper.py` to pass the key directly

### Customizing Search

Modify `judgment_loader.py` to adjust:
- Number of results returned (`max_results`)
- Relevance scoring algorithm
- Content extraction methods

## Limitations

- The app uses keyword-based search. For better semantic search, consider integrating embeddings (e.g., OpenAI embeddings, sentence transformers)
- LLM responses are based on available judgments only
- The app does not provide legal advice - it's a research tool

## Future Enhancements

- Semantic search using embeddings
- Advanced filtering by multiple features
- Export functionality for case references
- Comparison view for multiple cases
- Statistical analysis and trends

