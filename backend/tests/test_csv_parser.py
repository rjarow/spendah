"""Tests for CSV parser edge cases."""

import pytest
from pathlib import Path
import tempfile
import os

from app.parsers.csv_parser import CSVParser


class TestCSVParser:
    """Test CSV parser functionality."""

    @pytest.fixture
    def parser(self):
        return CSVParser()

    @pytest.fixture
    def temp_csv_file(self):
        """Create a temporary CSV file for testing."""

        def create_file(content: str):
            fd, path = tempfile.mkstemp(suffix=".csv")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            return Path(path)

        return create_file

    def test_can_parse_csv(self, parser):
        """Should recognize CSV files."""
        assert parser.can_parse(Path("test.csv")) is True
        assert parser.can_parse(Path("test.CSV")) is True
        assert parser.can_parse(Path("test.ofx")) is False

    def test_get_preview_basic(self, parser, temp_csv_file):
        """Should parse basic CSV and return preview."""
        content = "date,amount,description\n2024-01-15,-50.00,Grocery Store\n2024-01-16,-25.00,Gas Station"
        file_path = temp_csv_file(content)

        headers, rows = parser.get_preview(file_path)

        assert headers == ["date", "amount", "description"]
        assert len(rows) == 2

        os.unlink(file_path)

    def test_get_preview_limited_rows(self, parser, temp_csv_file):
        """Should limit preview rows."""
        lines = ["date,amount,description"] + [
            f"2024-01-{i},-{i}.00,Store {i}" for i in range(1, 20)
        ]
        content = "\n".join(lines)
        file_path = temp_csv_file(content)

        headers, rows = parser.get_preview(file_path, rows=5)

        assert len(rows) == 5

        os.unlink(file_path)

    def test_parse_signed_amounts(self, parser, temp_csv_file):
        """Should parse signed amounts correctly."""
        content = "date,amount,description\n2024-01-15,-50.00,Expense\n2024-01-16,100.00,Income"
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert len(transactions) == 2
        assert float(transactions[0]["amount"]) == -50.00
        assert float(transactions[1]["amount"]) == 100.00

        os.unlink(file_path)

    def test_parse_separate_debit_credit(self, parser, temp_csv_file):
        """Should handle separate debit/credit columns."""
        content = "date,debit,credit,description\n2024-01-15,50.00,,Grocery\n2024-01-16,,100.00,Refund"
        file_path = temp_csv_file(content)

        mapping = {
            "date_col": 0,
            "description_col": 3,
            "debit_col": 1,
            "credit_col": 2,
        }
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert len(transactions) == 2
        assert float(transactions[0]["amount"]) == -50.00  # debit: spending
        assert float(transactions[1]["amount"]) == 100.00  # credit: refund

        os.unlink(file_path)

    def test_parse_with_dollar_signs(self, parser, temp_csv_file):
        """Should strip dollar signs from amounts."""
        content = "date,amount,description\n2024-01-15,$50.00,Grocery"
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert float(transactions[0]["amount"]) == 50.00

        os.unlink(file_path)

    def test_parse_with_commas(self, parser, temp_csv_file):
        """Should handle amounts with thousand separators."""
        content = 'date,amount,description\n2024-01-15,"1,234.56",Large Purchase'
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert float(transactions[0]["amount"]) == 1234.56

        os.unlink(file_path)

    def test_parse_parentheses_negative(self, parser, temp_csv_file):
        """Should handle parentheses for negative amounts."""
        content = "date,amount,description\n2024-01-15,(50.00),Expense"
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert float(transactions[0]["amount"]) == -50.00

        os.unlink(file_path)

    def test_parse_skips_malformed_rows(self, parser, temp_csv_file):
        """Should skip rows that fail to parse."""
        content = "date,amount,description\n2024-01-15,-50.00,Grocery\nbad-date,-25.00,Gas\n2024-01-17,-10.00,Store"
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert len(transactions) == 2

        os.unlink(file_path)

    def test_parse_empty_amount_skipped(self, parser, temp_csv_file):
        """Should skip rows with empty amounts."""
        content = (
            "date,amount,description\n2024-01-15,,Empty Amount\n2024-01-16,-25.00,Valid"
        )
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert len(transactions) == 1

        os.unlink(file_path)

    def test_parse_insufficient_columns_skipped(self, parser, temp_csv_file):
        """Should skip rows with fewer columns than expected."""
        content = (
            "date,amount,description\n2024-01-15,-50.00\n2024-01-16,-25.00,Gas Station"
        )
        file_path = temp_csv_file(content)

        mapping = {"date_col": 0, "amount_col": 1, "description_col": 2}
        transactions = parser.parse(file_path, mapping, "%Y-%m-%d")

        assert len(transactions) == 1

        os.unlink(file_path)

    def test_parse_utf8_bom(self, parser, temp_csv_file):
        """Should handle UTF-8 BOM."""
        content = "\ufeffdate,amount,description\n2024-01-15,-50.00,Grocery"
        file_path = temp_csv_file(content)

        headers, rows = parser.get_preview(file_path)

        assert headers == ["date", "amount", "description"]

        os.unlink(file_path)
