"""
Base parser class for file parsing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from pathlib import Path


class BaseParser(ABC):
    """Base class for file parsers"""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file"""
        pass

    @abstractmethod
    def parse(
        self,
        file_path: Path,
        column_mapping: Dict[str, Any],
        date_format: str = "%Y-%m-%d"
    ) -> List[Dict[str, Any]]:
        """
        Parse file and return list of transaction dicts.
        Each dict should have: date, amount, raw_description
        """
        pass

    @abstractmethod
    def get_preview(
        self,
        file_path: Path,
        rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """Return (headers, preview_rows) for format confirmation"""
        pass
