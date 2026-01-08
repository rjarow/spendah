# Spendah Test Data

Synthetic transaction data for testing Spendah features.

## Files

### sample-transactions-2024.csv
**Format:** Chase-style CSV (Transaction Date, Description, Amount, Category)
**Date Format:** MM/DD/YYYY
**Amount Style:** Signed (negative = expense)
**Period:** January - June 2024

### sample-creditcard-2024.csv
**Format:** Generic credit card CSV (Date, Transaction, Amount, Type)
**Date Format:** YYYY-MM-DD
**Amount Style:** Separate columns (Type = Debit/Credit)
**Period:** January - June 2024

---

## Expected Recurring Patterns

### sample-transactions-2024.csv

| Merchant | Amount | Frequency | Notes |
|----------|--------|-----------|-------|
| Netflix | $15.99→$17.99 | Monthly | **Price increase in April** |
| Spotify | $10.99 | Monthly | Stable |
| Comcast Cable | $89.99→$94.99 | Monthly | **Price increase in June** |
| Eversource Energy | ~$76-142 | Monthly | Variable (utility) |
| OpenAI ChatGPT | $20.00 | Monthly | Stable |
| Apple.com/Bill | $2.99 | Monthly | Starts March (iCloud) |
| Payroll Deposit | $3,250 | Monthly | Income |

### sample-creditcard-2024.csv

| Merchant | Amount | Frequency | Notes |
|----------|--------|-----------|-------|
| Adobe Creative Cloud | $54.99→$59.99 | Monthly | **Price increase in April** |
| LinkedIn Premium | $29.99→$34.99 | Monthly | **Price increase in June** |
| GitHub Inc | $4.00 | Monthly | Stable |
| Planet Fitness | $24.99 | Monthly | Stable |
| Hulu | $17.99 | Monthly | Starts April |
| Credit Card Payment | ~$500-620 | Monthly | Variable (payment) |

---

## Edge Cases Included

### Price Increases (for Alert testing)
- Netflix: $15.99 → $17.99 (April 2024) - $2.00 increase
- Comcast: $89.99 → $94.99 (June 2024) - $5.00 increase  
- Adobe: $54.99 → $59.99 (April 2024) - $5.00 increase
- LinkedIn: $29.99 → $34.99 (June 2024) - $5.00 increase

### Large/Unusual Purchases (for Alert testing)
- Best Buy $249.99 (February) - Electronics
- Home Depot $234.56 (April) - Home improvement
- Airbnb $425.00 (June) - Travel
- Delta Airlines $342.00 (January) - Travel
- Marriott Hotels $289.50 (February) - Travel

### Variable Amounts (tests amount variance)
- Eversource Energy: $76.90 - $142.50 range
- Whole Foods: $78.90 - $95.67 range
- Costco Warehouse: $165.23 - $221.56 range
- Gas stations: $47.65 - $65.40 range

### New Subscriptions (for "new recurring" detection)
- Apple iCloud: Starts March 2024
- Hulu: Starts April 2024

### One-time vs Recurring
- Travel expenses (airlines, hotels, Airbnb) - Should NOT be detected as recurring
- Game purchases (Nintendo, Steam) - Should NOT be detected as recurring

---

## Import Instructions

1. Go to http://localhost:5173/import
2. Upload `sample-transactions-2024.csv`
3. AI should detect format with high confidence
4. Select/create account: "Chase Checking" (type: bank)
5. Confirm import

6. Upload `sample-creditcard-2024.csv`
7. Note: Different date format (YYYY-MM-DD) and amount style
8. Select/create account: "Rewards Credit Card" (type: credit)
9. Confirm import

---

## Testing Recurring Detection

After importing both files:

1. Go to http://localhost:5173/recurring
2. Click "Detect Recurring"
3. Should find ~10-12 patterns with high confidence:
   - Netflix (monthly, ~$17)
   - Spotify (monthly, $10.99)
   - Comcast (monthly, ~$91)
   - OpenAI (monthly, $20)
   - Apple iCloud (monthly, $2.99)
   - Adobe (monthly, ~$57)
   - LinkedIn (monthly, ~$31)
   - GitHub (monthly, $4)
   - Planet Fitness (monthly, $24.99)
   - Hulu (monthly, $17.99)
   
4. Should NOT detect as recurring:
   - Airlines, hotels (one-off travel)
   - Grocery stores (variable timing/amounts)
   - Gas stations (variable timing)

---

## Testing Dashboard

After import, navigate back in months to see data:
- January 2024 shows highest expenses (winter utilities)
- Dashboard month selector: ◄ to go back from current month
- Category breakdown should show Utilities, Shopping, Groceries as top

---

## Data Characteristics

- **96 transactions** in sample-transactions-2024.csv
- **52 transactions** in sample-creditcard-2024.csv
- **Total:** 148 transactions across 6 months
- **Categories:** 12+ different spending categories
- **Income:** Monthly payroll deposits ($3,250)
