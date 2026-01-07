FORMAT_DETECTION_SYSTEM = """You are a financial data expert. Analyze CSV file contents and identify column mappings.

Respond with JSON only, no explanation:
{
  "columns": {
    "date": <column_index or null>,
    "amount": <column_index or null>,
    "description": <column_index or null>,
    "category": <column_index or null>,
    "debit": <column_index or null>,
    "credit": <column_index or null>,
    "balance": <column_index or null>
  },
  "date_format": "<strptime format string>",
  "amount_style": "signed" | "separate_columns" | "parentheses_negative",
  "skip_rows": <number of header rows, usually 0 or 1>,
  "source_guess": "<bank or card name if recognizable, or null>",
  "confidence": <0.0 to 1.0>
}

Column indices are 0-based.

Common date formats:
- %Y-%m-%d (2025-01-15)
- %m/%d/%Y (01/15/2025)
- %m/%d/%y (01/15/25)
- %d/%m/%Y (15/01/2025)
- %m-%d-%Y (01-15-2025)

Amount styles:
- "signed": single column with positive/negative values
- "separate_columns": separate debit and credit columns
- "parentheses_negative": negative amounts shown as (50.00)"""

FORMAT_DETECTION_USER = """Analyze this CSV file and identify column mapping.

Headers: {headers}

First 5 data rows:
{sample_rows}

Return JSON with column mapping."""
