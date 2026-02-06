"""Tests for import service with balance extraction."""

import pytest
from pathlib import Path
from datetime import date
from decimal import Decimal
from app.parsers.ofx_parser import OFXParser


class TestOFXParserBalanceExtraction:
    """Test OFX parser balance extraction functionality."""

    def test_extract_balance_with_ledger_balance(self, tmp_path):
        """Test extracting balance from OFX file with ledger balance."""
        # Create a simple OFX file with balance information
        ofx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20240101000000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>0
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
</STMTTRNRS>
<STMTRS>
<BANKID>123456789
<BRANCHID>TEST BRANCH
<ACCTID>1234567890
<ACCTTYPE>CHECKING
<DTSTART>20240101000000
<DTEND>20240131000000>
<LEDGERBAL>
<BALAMT>1234.56</BALAMT>
<DTASOF>20240101000000</DTASOF>
</LEDGERBAL>
</STMTRS>
</BANKMSGSRSV1>
</OFX>
"""

        ofx_file = tmp_path / "test.ofx"
        ofx_file.write_bytes(ofx_content)

        parser = OFXParser()
        balance = parser.extract_balance(ofx_file)

        assert balance is not None
        assert balance == Decimal("1234.56")

    def test_extract_balance_with_available_balance(self, tmp_path):
        """Test extracting balance from OFX file with available balance."""
        ofx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20240101000000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>0
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
</STMTTRNRS>
<STMTRS>
<BANKID>123456789
<BRANCHID>TEST BRANCH
<ACCTID>1234567890
<ACCTTYPE>CHECKING
<DTSTART>20240101000000
<DTEND>20240131000000>
<AVAILBAL>
<BALAMT>567.89</BALAMT>
<DTASOF>20240101000000</DTASOF>
</AVAILBAL>
</STMTRS>
</BANKMSGSRSV1>
</OFX>
"""

        ofx_file = tmp_path / "test.ofx"
        ofx_file.write_bytes(ofx_content)

        parser = OFXParser()
        balance = parser.extract_balance(ofx_file)

        assert balance is not None
        assert balance == Decimal("567.89")

    def test_extract_balance_no_balance(self, tmp_path):
        """Test extracting balance from OFX file with no balance information."""
        ofx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20240101000000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>0
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
</STMTTRNRS>
<STMTRS>
<BANKID>123456789
<BRANCHID>TEST BRANCH
<ACCTID>1234567890
<ACCTTYPE>CHECKING
<DTSTART>20240101000000
<DTEND>20240131000000
</STMTRS>
</BANKMSGSRSV1>
</OFX>
"""

        ofx_file = tmp_path / "test.ofx"
        ofx_file.write_bytes(ofx_content)

        parser = OFXParser()
        balance = parser.extract_balance(ofx_file)

        assert balance is None

    def test_extract_balance_negative_amount(self, tmp_path):
        """Test extracting negative balance from OFX file."""
        ofx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20240101000000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>0
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
</STMTTRNRS>
<STMTRS>
<BANKID>123456789
<BRANCHID>TEST BRANCH
<ACCTID>1234567890
<ACCTTYPE>SAVINGS
<DTSTART>20240101000000
<DTEND>20240131000000>
<LEDGERBAL>
<BALAMT>-250.00</BALAMT>
<DTASOF>20240101000000</DTASOF>
</LEDGERBAL>
</STMTRS>
</BANKMSGSRSV1>
</OFX>
"""

        ofx_file = tmp_path / "test.ofx"
        ofx_file.write_bytes(ofx_content)

        parser = OFXParser()
        balance = parser.extract_balance(ofx_file)

        assert balance is not None
        assert balance == Decimal("-250.00")
