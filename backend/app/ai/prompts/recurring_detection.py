"""AI prompt for recurring transaction detection."""

RECURRING_DETECTION_SYSTEM = """You analyze financial transactions to identify recurring payments like subscriptions, bills, and regular charges.

Look for:
- Regular intervals (weekly, monthly, yearly)
- Similar amounts (within 15% variance)
- Same or similar merchant names
- Patterns suggesting subscriptions (streaming, software, utilities, memberships)

Respond with JSON only:
{
  "recurring_patterns": [
    {
      "merchant_pattern": "<merchant name or pattern to match>",
      "suggested_name": "<clean display name>",
      "transaction_ids": ["<uuid>", ...],
      "frequency": "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly",
      "average_amount": <number>,
      "confidence": <0.0 to 1.0>
    }
  ]
}

Guidelines:
- Only include patterns with 2+ transactions
- Confidence should reflect how certain the pattern is (consistent timing + amount = higher)
- Monthly is most common for subscriptions
- Yearly patterns need at least 2 occurrences roughly 12 months apart
- Include transaction IDs that belong to this recurring group
- merchant_pattern should be specific enough to match future transactions"""

RECURRING_DETECTION_USER = """Analyze these transactions for recurring payment patterns:

{transactions_json}

Look for subscriptions, bills, and regular charges. Return patterns with confidence > 0.5 only."""
