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

    def extract_balance(self, file_path: Path) -> Optional[Decimal]:
        """
        Extract balance information from OFX file.

        OFX files often contain balance information in:
        - Ledger balance (<LEDGERBAL><BALAMT>)
        - Available balance (<BALAMT> within <AVGBAL>)

        Returns:
            Balance as Decimal, or None if no balance information found
        """
        try:
            with open(file_path, 'rb') as f:
                ofx = OFXParseLib.parse(f)

            # OFX files can have multiple accounts
            # We'll return the first account's ledger balance
            if ofx.accounts and len(ofx.accounts) > 0:
                account = ofx.accounts[0]
                # Ledger balance is the total balance of the account
                balance = getattr(account.statement, 'balance', None)
                if balance is not None:
                    return Decimal(str(balance))

                # Available balance (if ledger balance is not available)
                available_balance = getattr(account.statement, 'available_balance', None)
                if available_balance is not None:
                    return Decimal(str(available_balance))

            return None
        except Exception as e:
            print(f"Error extracting balance from OFX: {e}")
            return None
