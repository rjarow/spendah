"""
CSV file parser.
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from app.parsers.base import BaseParser


class CSVParser(BaseParser):
    """Parser for CSV bank/card exports"""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.csv'

    def get_preview(
        self,
        file_path: Path,
        rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """Return headers and preview rows"""
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(8192)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel

            reader = csv.reader(f, dialect)
            headers = next(reader, [])

            preview_rows = []
            for i, row in enumerate(reader):
                if i >= rows:
                    break
                preview_rows.append(row)

            return headers, preview_rows

    def parse(
        self,
        file_path: Path,
        column_mapping: Dict[str, Any],
        date_format: str = "%Y-%m-%d"
    ) -> List[Dict[str, Any]]:
        """Parse CSV and return transaction dicts"""
        transactions = []

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            try:
                dialect = csv.Sniffer().sniff(f.read(8192))
                f.seek(0)
            except csv.Error:
                dialect = csv.excel
                f.seek(0)

            reader = csv.reader(f, dialect)
            next(reader)

            for row in reader:
                if not row or all(cell.strip() == '' for cell in row):
                    continue

                try:
                    txn = self._parse_row(row, column_mapping, date_format)
                    if txn:
                        transactions.append(txn)
                except Exception as e:
                    print(f"Error parsing row {row}: {e}")
                    continue

        return transactions

    def _parse_row(
        self,
        row: List[str],
        mapping: Dict[str, Any],
        date_format: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a single row into a transaction dict"""

        date_str = row[mapping['date_col']].strip()
        txn_date = datetime.strptime(date_str, date_format).date()

        amount = self._parse_amount(row, mapping)
        if amount is None:
            return None

        description = row[mapping['description_col']].strip()

        return {
            'date': txn_date,
            'amount': amount,
            'raw_description': description
        }

    def _parse_amount(
        self,
        row: List[str],
        mapping: Dict[str, Any]
    ) -> Optional[Decimal]:
        """Parse amount handling various formats"""

        if mapping.get('debit_col') is not None and mapping.get('credit_col') is not None:
            debit = self._clean_amount(row[mapping['debit_col']])
            credit = self._clean_amount(row[mapping['credit_col']])

            if debit and debit > 0:
                return -debit
            elif credit and credit > 0:
                return credit
            return Decimal('0')

        amount_str = row[mapping['amount_col']]
        return self._clean_amount(amount_str)

    def _clean_amount(self, amount_str: str) -> Optional[Decimal]:
        """Clean and parse amount string"""
        if not amount_str or not amount_str.strip():
            return None

        amount_str = amount_str.strip()

        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]

        amount_str = re.sub(r'[$,]', '', amount_str)

        try:
            return Decimal(amount_str)
        except InvalidOperation:
            return None
