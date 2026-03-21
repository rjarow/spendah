"""
CSV file parser.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from app.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """Parser for CSV bank/card exports"""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".csv"

    def get_preview(
        self, file_path: Path, rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """
        Get a preview of the CSV file for column mapping.
        Returns (headers, preview_rows)
        """
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader)
            if not headers:
                raise ValueError("CSV file has no headers")

            preview_rows = []
            for i in range(rows):
                try:
                    row = next(reader)
                    preview_rows.append(row)
                except StopIteration:
                    break
            return headers, preview_rows

    def parse(
        self,
        file_path: Path,
        column_mapping: Dict[str, int],
        date_format: str = "%Y-%m-%d",
    ) -> List[Dict[str, Any]]:
        """
        Parse the CSV file and return list of transaction dicts.
        """
        transactions = []

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader)

            for row_num, row in enumerate(reader, start=2):
                try:
                    txn = self._parse_row(row, column_mapping, date_format)
                    if txn:
                        transactions.append(txn)
                except Exception as e:
                    logger.warning(f"Error parsing row {row_num}: {e}")
                    continue

            return transactions

    def _parse_row(
        self, row: List[str], mapping: Dict[str, Any], date_format: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a single row into a transaction dict"""

        max_col = max(
            mapping.get("date_col", 0),
            mapping.get("amount_col", 0),
            mapping.get("description_col", 0),
            mapping.get("debit_col", 0) or 0,
            mapping.get("credit_col", 0) or 0,
            mapping.get("account_col", 0) or 0,
        )
        if len(row) <= max_col:
            logger.warning(
                f"Row has {len(row)} columns but mapping requires {max_col + 1}"
            )
            return None

        date_str = row[mapping["date_col"]].strip()
        logger.debug(f"Parsing date: {date_str!r} with format: {date_format!r}")
        txn_date = datetime.strptime(date_str, date_format).date()
        logger.debug(f"Parsed date: {txn_date!r}")

        amount = self._parse_amount(row, mapping)
        if amount is None:
            return None

        description = row[mapping["description_col"]].strip()

        result = {"date": txn_date, "amount": amount, "raw_description": description}

        if mapping.get("account_col") is not None and len(row) > mapping["account_col"]:
            account_name = row[mapping["account_col"]].strip()
            if account_name:
                result["account_name"] = account_name

        return result

    def _parse_amount(
        self, row: List[str], mapping: Dict[str, Any]
    ) -> Optional[Decimal]:
        """
        Parse amount from row using column mapping.

        Supports three styles:
        1. Single amount column (signed positive/negative)
        2. Separate debit/credit columns
        """
        try:
            if "debit_col" in mapping and mapping["debit_col"] is not None:
                debit_val = (
                    row[mapping["debit_col"]].strip()
                    if len(row) > mapping["debit_col"]
                    else ""
                )
                credit_val = ""
                if "credit_col" in mapping and mapping["credit_col"] is not None:
                    credit_val = (
                        row[mapping["credit_col"]].strip()
                        if len(row) > mapping["credit_col"]
                        else ""
                    )

                debit = self._parse_decimal(debit_val) if debit_val else Decimal("0")
                credit = self._parse_decimal(credit_val) if credit_val else Decimal("0")

                return credit - debit
            elif "amount_col" in mapping:
                amount_str = row[mapping["amount_col"]].strip()
                if not amount_str:
                    return None
                return self._parse_decimal(amount_str)
            else:
                logger.warning("No amount column specified in mapping")
                return None
        except (InvalidOperation, ValueError, IndexError) as e:
            logger.warning(f"Failed to parse amount: {e}")
            return None

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse a decimal value, handling common formats."""
        cleaned = value.strip()
        cleaned = re.sub(r"[$,]", "", cleaned)
        cleaned = cleaned.replace("(", "-").replace(")", "")
        if not cleaned or cleaned == "-":
            return Decimal("0")
        return Decimal(cleaned)
