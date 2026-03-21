"""
Prompts for the AI coach.
"""

COACH_SYSTEM_PROMPT = """You are a friendly, knowledgeable personal finance coach. You have access to the user's financial data and can answer questions about their spending, subscriptions, and financial patterns.

## Your Personality
- Warm and encouraging, never judgmental
- Direct and concise - respect the user's time
- Proactive with insights when relevant
- Honest about limitations

## What You Know
You have access to:
- Transaction history (tokenized as MERCHANT_XXX with category hints)
- Recurring charges and subscriptions
- Spending trends and comparisons
- Recent alerts and anomalies

## What You Can Do
- Answer questions about spending ("How much did I spend on dining?")
- Explain trends ("Why is my spending up this month?")
- Review subscriptions ("What subscriptions do I have?")
- Provide context ("Is this normal for my spending?")
- Offer suggestions (without being pushy)

## What You Cannot Do
- Access real merchant names (you see tokens like MERCHANT_042)
- Make purchases or changes on behalf of the user
- Provide investment advice or recommendations
- Access data outside what's provided in context

## Response Guidelines
- Keep responses concise (2-4 sentences for simple questions)
- Use specific numbers when available
- Acknowledge uncertainty when data is incomplete
- Ask clarifying questions if the request is ambiguous

## Privacy Note
The user's data is tokenized for privacy. When you see "MERCHANT_042 [Groceries]", the system will replace this with the actual merchant name before showing the user. Speak naturally as if you know the merchant names.

Current date context: {current_date}
"""

CONTEXT_ASSEMBLY_PROMPT = """Based on the user's question, determine what financial context would be helpful.

User question: {question}

Available context types:
1. recent_transactions - Last 30 days of transactions
2. category_spending - Spending by category for current/previous months
3. recurring_charges - All detected recurring charges
4. alerts - Recent alerts and anomalies
5. trends - Month-over-month comparisons

Return a JSON array of context types needed (max 3 for efficiency):
["category_spending", "recurring_charges"]

Only include what's actually relevant to answer the question."""

TITLE_GENERATION_PROMPT = """Generate a short title (max 6 words) for this conversation based on the first message.

First message: {message}

Return only the title, no quotes or explanation."""

SUMMARY_GENERATION_PROMPT = """Summarize this conversation in 1-2 sentences for future context.

Messages:
{messages}

Focus on: key topics discussed, any decisions made, follow-up items.
Return only the summary."""


def build_coach_prompt(
    user_message: str, context: dict, conversation_history: list = None
) -> str:
    """Build the full prompt for the coach with context."""

    prompt_parts = []

    if conversation_history:
        prompt_parts.append("## Previous Messages in This Conversation")
        for msg in conversation_history[-10:]:
            role = "User" if msg["role"] == "user" else "Coach"
            prompt_parts.append(f"{role}: {msg['content']}")
        prompt_parts.append("")

    prompt_parts.append("## Your Financial Context")

    if "spending_context" in context:
        sc = context["spending_context"]

        if "recent_transactions" in sc:
            prompt_parts.append("\n### Recent Transactions (Last 90 Days)")
            for txn in sc["recent_transactions"][:20]:
                prompt_parts.append(
                    f"- {txn['date']}: {txn['merchant']} ${abs(txn['amount']):.2f}"
                )
            if len(sc.get("recent_transactions", [])) > 20:
                prompt_parts.append(
                    f"  ... and {len(sc['recent_transactions']) - 20} more transactions"
                )

        if "monthly_by_category" in sc:
            prompt_parts.append("\n### Monthly Spending by Category")
            sorted_months = sorted(sc["monthly_by_category"].keys(), reverse=True)
            for month in sorted_months[:6]:
                categories = sc["monthly_by_category"][month]
                items = [
                    f"{cat}: ${amt:.2f}"
                    for cat, amt in sorted(
                        categories.items(), key=lambda x: x[1], reverse=True
                    )[:5]
                ]
                prompt_parts.append(f"{month}: {', '.join(items)}")

        if "trends" in sc:
            trends = sc["trends"]
            prompt_parts.append("\n### Spending Trends")
            if trends.get("current_month_total"):
                prompt_parts.append(
                    f"- Current month total: ${trends['current_month_total']:,.2f}"
                )
            if trends.get("avg_monthly_total"):
                prompt_parts.append(
                    f"- Average monthly: {trends['avg_monthly_total']:,.2f}"
                )
            if trends.get("month_change_pct"):
                direction = "up" if trends["month_change_pct"] > 0 else "down"
                prompt_parts.append(
                    f"- Month over month: {abs(trends['month_change_pct']):.1f}% {direction}"
                )
            if trends.get("months_with_data"):
                prompt_parts.append(
                    f"- Data available: {trends['months_with_data']} months"
                )

            if "category_trends" in trends:
                prompt_parts.append("\n### Category Trends (vs 3-month avg)")
                for cat, data in sorted(
                    trends["category_trends"].items(),
                    key=lambda x: abs(x[1].get("change_pct", 0)),
                    reverse=True,
                )[:5]:
                    change = data.get("change_pct", 0)
                    direction = "up" if change > 0 else "down"
                    prompt_parts.append(
                        f"- {cat}: {data['current']:,.2f} ({abs(change):.0f}% {direction} vs avg)"
                    )

    if "recurring_charges" in context:
        prompt_parts.append("\n### Recurring Charges")
        for rec in context["recurring_charges"]:
            prompt_parts.append(
                f"- {rec['name']}: {rec['amount']:,.2f}/{rec['frequency']}"
            )

    if "alerts" in context:
        prompt_parts.append("\n### Recent Alerts")
        for alert in context["alerts"][:5]:
            prompt_parts.append(f"- {alert['title']}")

    prompt_parts.append(f"\n## User's Question\n{user_message}")

    return "\n".join(prompt_parts)
