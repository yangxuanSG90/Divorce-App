#!/bin/bash
# Script to run the Streamlit app

cd "$(dirname "$0")/.."
streamlit run app/app.py

