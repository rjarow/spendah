import { test, expect } from '@playwright/test'

test.describe('Navigation & Layout', () => {
  test('app loads and shows dashboard', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=Spendah').first()).toBeVisible()
    await expect(page.locator('text=Dashboard').first()).toBeVisible()
  })

  test('sidebar links navigate to all pages', async ({ page }) => {
    await page.goto('/')

    const routes = [
      { link: 'Transactions', heading: /transactions/i },
      { link: 'Budgets', heading: /budgets/i },
      { link: 'Accounts', heading: /accounts/i },
      { link: 'Net Worth', heading: /net worth/i },
      { link: 'Import', heading: /import/i },
      { link: 'Coach', heading: /financial coach|coach/i },
      { link: 'Settings', heading: /settings/i },
    ]

    for (const { link, heading } of routes) {
      await page.getByRole('link', { name: link }).click()
      await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible()
    }
  })

  test('dashboard shows key sections', async ({ page }) => {
    await page.goto('/')

    // Month navigation
    await expect(page.locator('button:has-text("◄")').or(page.locator('button:has-text("←")')).first()).toBeVisible()

    // Key stat cards should render (even if empty)
    await expect(page.getByText(/spent|income|net/i).first()).toBeVisible()
  })

  test('unknown route does not crash', async ({ page }) => {
    const response = await page.goto('/nonexistent-page')
    // App should load without a server error (200 from SPA)
    expect(response?.status()).toBeLessThan(500)
  })
})
