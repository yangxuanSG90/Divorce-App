# Quick Start Guide

## Installation

1. **Install dependencies:**
   ```bash
   cd app
   pip install -r requirements.txt
   ```

2. **(Optional) Set OpenAI API key for better responses:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   If you don't set this, the app will use a simple fallback method.

## Running the App

### Option 1: Using the run script
```bash
cd app
./run.sh
```

### Option 2: Direct Streamlit command
```bash
cd app
streamlit run app.py
```

Or from the parent directory:
```bash
streamlit run app/app.py
```

### Option 3: Using Python module
```bash
python -m streamlit run app/app.py
```

## First Use

1. The app will automatically load the judgment index from `../judgment_index.csv`
2. It will load all MD files from `../Sample PDFs/`
3. Open your browser to `http://localhost:8501`

## Example Questions

Try asking:
- "What are typical outcomes for cases involving adultery?"
- "How are child custody matters typically handled?"
- "What factors affect maintenance awards?"
- "What happens in contested divorce cases?"

## Troubleshooting

### App won't start
- Make sure you're in the correct directory
- Check that `judgment_index.csv` exists in the parent directory
- Verify that `Sample PDFs/` folder exists with MD files

### No answers generated
- Check if you have relevant cases in the database
- Try rephrasing your question with different keywords
- If using OpenAI, verify your API key is set correctly

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that Python version is 3.9 or higher

