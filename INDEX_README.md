# Judgment Index Documentation

## Overview

This index contains high-value features extracted from all MD judgment files in the `Sample PDFs` folder. The index is available in two formats:
- **JSON**: `judgment_index.json` - Full structured data with nested objects
- **CSV**: `judgment_index.csv` - Flattened format for spreadsheet analysis

## Features Extracted

### Structured Features (from court metadata)

1. **case_id** (hashed): Unique identifier derived from case citation
2. **filing_date**: Date when the divorce was filed
3. **judgment_date**: Date when judgment was delivered
4. **court_level**: Family Court / High Court / Court of Appeal
5. **judge_id** (hashed): Pseudonymised judge identifier
6. **judge_name**: Name of the presiding judge
7. **applicant_role_age_range**: Age range of applicant (e.g., "30-39", "40-49")
8. **respondent_role_age_range**: Age range of respondent
9. **number_of_witnesses**: Count of witnesses mentioned
10. **contested**: Boolean indicating if hearings were contested
11. **legal_representation**: Status (both_represented / one_represented / both_pro_se / unknown)
12. **maintenance**: Boolean - maintenance issues present
13. **custody**: Boolean - custody issues present
14. **division_of_assets**: Boolean - asset division issues present
15. **prior_cases_between_parties**: Boolean - mentions of prior cases

### Text-Derived Features

1. **topic_tags**: List of topics identified (child_custody, adultery, cruelty, financials, domestic_violence, separation)
2. **mention_of_domestic_violence**: Boolean - explicit mention of domestic violence
3. **mention_of_adultery**: Boolean - explicit mention of adultery
4. **legal_issue_counts**: Count of disputed legal issues/transactions
5. **sentiment_score**: Judge tone score (-1 to 1, where positive = more positive tone)

### Derived Aggregated Features

1. **days_between_filing_and_judgment**: Number of days from filing to judgment
2. **child_ages_present**: Object with min/max/median child ages
3. **asset_value_bucket**: Categorized asset values (<100k, 100k-500k, 500k-1M, >1M)

## Usage

### JSON Format
```python
import json
with open('judgment_index.json', 'r') as f:
    index = json.load(f)
    
# Access features
for case in index:
    print(f"Case: {case['case_id']}")
    print(f"Court: {case['court_level']}")
    print(f"Topics: {', '.join(case['topic_tags'])}")
```

### CSV Format
The CSV can be opened in Excel, Google Sheets, or any spreadsheet application for easy filtering and analysis.

## Current Index Statistics

- **Total Cases**: 3
- **Family Court Cases**: 3
- **Contested Cases**: 1
- **Cases with Adultery Mention**: 2
- **Cases with Domestic Violence Mention**: 1

## Notes

- Case IDs and Judge IDs are hashed for privacy/anonymization
- Some features may be `null` if information is not available in the source documents
- Sentiment scores are calculated using NLTK's VADER sentiment analyzer
- Asset value buckets are estimated based on monetary amounts mentioned in judgments

## Regenerating the Index

To regenerate the index after adding new MD files:

```bash
python3 create_judgment_index.py
```

This will process all `.md` files in the `Sample PDFs` folder and update both JSON and CSV index files.

