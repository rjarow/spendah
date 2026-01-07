"""
OFX/QFX file parser.
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from decimal import Decimal

from ofxparse import OfxParser as OFXParseLib

from app.parsers.base import BaseParser


class OFXParser(BaseParser):
    """Parser for OFX/QFX bank exports"""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.ofx', '.qfx']

    def get_preview(
        self,
        file_path: Path,
        rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """Return headers and preview rows for OFX"""
        headers = ['Date', 'Amount', 'Description', 'Type', 'ID']

        with open(file_path, 'rb') as f:
            ofx = OFXParseLib.parse(f)

        preview_rows = []
        for account in ofx.accounts:
            for txn in account.statement.transactions[:rows]:
                preview_rows.append([
                    txn.date.strftime('%Y-%m-%d'),
                    str(txn.amount),
                    txn.memo or txn.payee or '',
                    txn.type,
                    txn.id
                ])
                if len(preview_rows) >= rows:
                    break
            if len(preview_rows) >= rows:
                break

        return headers, preview_rows

    def parse(
        self,
        file_path: Path,
        column_mapping: Optional[Dict[str, Any]] = None,
        date_format: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Parse OFX and return transaction dicts"""
        transactions = []

        with open(file_path, 'rb') as f:
            ofx = OFXParseLib.parse(f)

        for account in ofx.accounts:
            for txn in account.statement.transactions:
                description = txn.memo or txn.payee or f"Transaction {txn.id}"

                transactions.append({
                    'date': txn.date.date() if hasattr(txn.date, 'date') else txn.date,
                    'amount': Decimal(str(txn.amount)),
                    'raw_description': description.strip()
                })

        return transactions
