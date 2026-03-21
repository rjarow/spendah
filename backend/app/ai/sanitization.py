"""
Prompt sanitization utilities to prevent prompt injection attacks.
"""

import re
from typing import Optional


SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all|prior)", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|above|all|prior)", re.IGNORECASE),
    re.compile(r"forget\s+(previous|above|all|prior)", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"assistant\s*:", re.IGNORECASE),
    re.compile(r"user\s*:", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"new\s+instructions?", re.IGNORECASE),
    re.compile(r"override\s+(previous|default|system)", re.IGNORECASE),
    re.compile(r"print\s+(all|everything|your|the)", re.IGNORECASE),
    re.compile(r"reveal\s+(all|everything|your|the|prompt)", re.IGNORECASE),
    re.compile(r"show\s+(me\s+)?(all|everything|your|the|prompt)", re.IGNORECASE),
    re.compile(r"output\s+(all|everything|your|the|prompt)", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|prompt|instructions?)\s*>", re.IGNORECASE),
    re.compile(r"\[\s*system\s*\]", re.IGNORECASE),
    re.compile(r"\{\s*system\s*\}", re.IGNORECASE),
]


def sanitize_for_prompt(text: Optional[str], max_length: int = 500) -> str:
    """
    Sanitize user input before including it in AI prompts.

    Args:
        text: The text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text safe for inclusion in prompts
    """
    if not text:
        return ""

    sanitized = str(text)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    sanitized = sanitized.replace("{", "{{").replace("}", "}}")

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(sanitized):
            sanitized = re.sub(r"[^\w\s\-\.,'\"]", "", sanitized)
            break

    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", sanitized)

    return sanitized.strip()


def sanitize_merchant_name(name: Optional[str]) -> str:
    """Sanitize merchant name for prompts."""
    return sanitize_for_prompt(name, max_length=100)


def sanitize_description(description: Optional[str]) -> str:
    """Sanitize transaction description for prompts."""
    return sanitize_for_prompt(description, max_length=200)
