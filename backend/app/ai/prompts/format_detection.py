"""Format detection prompt with structural redaction for privacy."""

import re
from typing import List, Tuple
from datetime import date, timedelta
import random


def redact_sample_rows(
    headers: List[str],
    rows: List[List[str]],
    date_shift_days: int = 937
) -> Tuple[List[str], List[List[str]]]:
    """
    Redact sample rows while preserving structure for format detection.

    - Dates: Shifted by random offset
    - Amounts: Replaced with XXX.XX pattern (preserving sign/format)
    - Descriptions: Replaced with REDACTED_MERCHANT_A, B, C...
    - Other text: Replaced with REDACTED
    """
    redacted_rows = []
    merchant_counter = 0
    merchant_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for row in rows:
        redacted_row = []
        for i, cell in enumerate(row):
            cell_str = str(cell).strip()

            # Try to detect and redact appropriately
            redacted = redact_cell(
                cell_str,
                headers[i] if i < len(headers) else "",
                date_shift_days,
                merchant_labels[merchant_counter % len(merchant_labels)]
            )

            # Track if this looks like a merchant column
            if "REDACTED_MERCHANT" in redacted:
                merchant_counter += 1

            redacted_row.append(redacted)

        redacted_rows.append(redacted_row)

    return headers, redacted_rows


def redact_cell(cell: str, header: str, date_shift: int, merchant_label: str) -> str:
    """Redact a single cell based on its content pattern."""

    # Empty cell
    if not cell:
        return ""

    # Date patterns
    date_patterns = [
        r'^\d{1,2}/\d{1,2}/\d{2,4}$',
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{1,2}-\d{1,2}-\d{2,4}$',
    ]
    for pattern in date_patterns:
        if re.match(pattern, cell):
            # Return a shifted fake date in same format
            try:
                fake_date = date.today() + timedelta(days=date_shift)
                if '/' in cell:
                    return fake_date.strftime("%m/%d/%Y")
                else:
                    return fake_date.isoformat()
            except:
                return "XX/XX/XXXX"

    # Amount patterns (preserve format but hide value)
    amount_patterns = [
        (r'^-?\$?[\d,]+\.\d{2}$', lambda m: "-XXX.XX" if m.startswith('-') else "XXX.XX"),
        (r'^\([\d,]+\.\d{2}\)$', lambda m: "(XXX.XX)"),
        (r'^-?[\d,]+\.\d{2}$', lambda m: "-XXX.XX" if m.startswith('-') else "XXX.XX"),
    ]
    for pattern, replacer in amount_patterns:
        if re.match(pattern, cell.replace(',', '').replace('$', '')):
            return replacer(cell)

    # Header hints for description/merchant columns
    desc_headers = ['description', 'merchant', 'payee', 'memo', 'details', 'name']
    if any(h in header.lower() for h in desc_headers):
        # Check for person payment patterns
        if any(svc in cell.upper() for svc in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP']):
            service = next(s for s in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP'] if s in cell.upper())
            return f"{service} REDACTED_PERSON"
        return f"REDACTED_MERCHANT_{merchant_label}"

    # Check if it looks like a merchant/description anyway
    if len(cell) > 10 and not cell.replace('.','').replace(',','').isdigit():
        if any(svc in cell.upper() for svc in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP']):
            service = next(s for s in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP'] if s in cell.upper())
            return f"{service} REDACTED_PERSON"
        return f"REDACTED_MERCHANT_{merchant_label}"

    # Account numbers (mask all but format)
    if re.match(r'^[\d\-\*]+$', cell) and len(cell) > 4:
        return "****" + cell[-4:] if len(cell) >= 4 else "****"

    # Default: keep short values, redact longer ones
    if len(cell) <= 3:
        return cell

    return "REDACTED"


# System prompt for format detection (unchanged but now receives redacted data)
FORMAT_DETECTION_SYSTEM = """You are a financial data expert. Analyze CSV file contents and identify column mappings.

The data has been redacted for privacy. Look at the STRUCTURE, not the values:
- Dates: Shown as shifted dates (still in original format)
- Amounts: Shown as XXX.XX (preserving sign and format)
- Descriptions: Shown as REDACTED_MERCHANT_A, REDACTED_MERCHANT_B, etc.
- Person payments: Shown as VENMO REDACTED_PERSON, etc.

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

First 5 data rows (redacted for privacy):
{sample_rows}

Return JSON with column mapping."""
