import { Page, expect } from '@playwright/test'

const API_BASE = 'http://localhost:8000/api/v1'

/**
 * Reset the database to a clean state via API.
 * Creates a fresh test account and category.
 */
export async function resetTestData(page: Page) {
  // We use page.request so cookies/context are shared
  const req = page.request

  // Create a test account
  const accountRes = await req.post(`${API_BASE}/accounts`, {
    data: { name: 'Test Checking', account_type: 'checking', current_balance: 5000 },
  })
  const account = await accountRes.json()

  // Fetch existing categories
  const catRes = await req.get(`${API_BASE}/categories`)
  const categories = await catRes.json()

  return {
    account,
    categories: categories.items || categories,
  }
}

/**
 * Navigate and wait for the page to be fully loaded.
 */
export async function navigateTo(page: Page, path: string) {
  await page.goto(path)
  // Wait for the sidebar to render (indicates app is loaded)
  await expect(page.locator('text=Spendah').first()).toBeVisible({ timeout: 10000 })
}

/**
 * Create a test CSV file content for import testing.
 */
export function testCSVContent(): string {
  const today = new Date()
  const fmt = (d: Date) => d.toISOString().split('T')[0]
  const daysAgo = (n: number) => {
    const d = new Date(today)
    d.setDate(d.getDate() - n)
    return fmt(d)
  }

  return [
    'date,amount,description',
    `${daysAgo(1)},-45.50,WHOLE FOODS #1234`,
    `${daysAgo(2)},-12.99,SPOTIFY PREMIUM`,
    `${daysAgo(3)},-85.00,SHELL GAS STATION`,
    `${daysAgo(4)},2500.00,DIRECT DEPOSIT PAYROLL`,
    `${daysAgo(5)},-32.50,CHIPOTLE MEXICAN GRILL`,
  ].join('\n')
}
