---
type: note
title: Balance Import from Transaction Files Implementation
created: 2026-02-05
tags:
  - import
  - balance
  - OFX
  - backend
related:
  - "[[Phase-06-NetWorth-Polish-Integration]]"
---

# Balance Import from Transaction Files

## Overview

Implemented automatic balance extraction from OFX/QFX transaction files, allowing users to import their account balances directly from bank statements.

## Implementation Details

### 1. OFX Parser Enhancements (`backend/app/parsers/ofx_parser.py`)

Added `extract_balance()` method to extract balance information from OFX files:

- **Ledger Balance Support**: Extracts `BALAMT` from `<STMTRS>` section
- **Available Balance Support**: Falls back to `AVGBAL` if ledger balance is not available
- **Error Handling**: Gracefully handles files without balance information
- **Multiple Account Support**: Returns balance from first account in OFX file

```python
def extract_balance(self, file_path: Path) -> Optional[Decimal]:
    """Extract balance from OFX file."""
    with open(file_path, 'rb') as f:
        ofx = OFXParseLib.parse(f)

    if ofx.accounts and len(ofx.accounts) > 0:
        account = ofx.accounts[0]
        if account.statement.balance is not None:
            return Decimal(str(account.statement.balance))
        if account.statement.available_balance is not None:
            return Decimal(str(account.statement.available_balance))

    return None
```

### 2. Import Service Updates (`backend/app/services/import_service.py`)

Modified `get_preview_with_ai()` to include extracted balance:

- **Balance Extraction**: Calls `extract_balance()` for OFX files
- **Balance Storage**: Stores extracted balance in `PENDING_IMPORTS` dictionary
- **Balance Formatting**: Converts Decimal to float for JSON serialization

Updated balance processing in import functions:

- **Balance Application**: New `update_balance` field in `ImportConfirmRequest`
- **Balance Storage**: Stores extracted balance from file
- **Balance Application**: Updates account balance when checkbox is checked

```python
# In get_preview_with_ai()
if isinstance(parser, CSVParser):
    detected_format = await detect_csv_format(headers, preview_rows)
else:
    balance = parser.extract_balance(file_path)

PENDING_IMPORTS[import_id] = {
    'file_path': str(file_path),
    'filename': filename,
    'parser_type': type(parser).__name__,
    'detected_format': detected_format,
    'extracted_balance': float(balance) if balance else None
}
```

### 3. Schema Updates (`backend/app/schemas/import_file.py`)

Added balance-related fields to schemas:

**ImportUploadResponse**:
- `extracted_balance`: Optional[float] - Balance extracted from file

**ImportConfirmRequest**:
- `update_balance`: bool = False - Whether to update account balance
- `new_balance`: Optional[float] - New balance to apply

### 4. Test Coverage (`backend/tests/test_import_balance.py`)

Created comprehensive test suite covering:

- **Ledger Balance Extraction**: Verifies BALAMT extraction
- **Available Balance Extraction**: Verifies AVGBAL extraction
- **No Balance Scenario**: Handles files without balance information
- **Negative Balances**: Verifies negative balance extraction
- **OFX File Format**: Tests various OFX file structures

## Integration Flow

1. **User Uploads OFX File**: File is parsed and balance is extracted
2. **Preview Display**: API response includes `extracted_balance` field
3. **User Confirmation**: User can optionally update account balance
4. **Balance Application**: When checkbox is checked, balance is applied to account
5. **Balance Update**: Account's `current_balance` and `balance_updated_at` are updated

## User Experience

**Before Import**:
```
This file shows a balance of $1,234.56
[ ] Update account balance to $1,234.56
```

**After Import**:
- Account balance is automatically updated if checkbox is checked
- Balance is updated alongside transaction import
- Import log records successful balance updates

## Benefits

1. **Convenience**: Users don't need to manually enter starting balances
2. **Accuracy**: Bank-verified balances reduce manual entry errors
3. **Consistency**: Imported balances match bank records exactly
4. **Audit Trail**: Balance update timestamped in account record
5. **Backward Compatible**: Works with existing import flow without breaking changes

## Technical Notes

- **Balance Storage**: Uses existing `current_balance` field in Account model
- **Balance Timestamp**: Updates `balance_updated_at` field to track when balance was last set
- **Error Handling**: If balance extraction fails, import continues normally
- **No Breaking Changes**: Existing CSV import flow remains unchanged

## Future Enhancements

1. **CSV Balance Support**: Extend balance extraction to CSV files
2. **Balance Validation**: Compare extracted balance with calculated balance
3. **Balance History**: Record balance snapshots for history tracking
4. **Auto-Balance Sync**: Suggest balance updates when import completes
5. **Balance Diff View**: Show before/after balance comparison
