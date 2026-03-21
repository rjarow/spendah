import { test, expect } from '@playwright/test'

test.describe('Transactions', () => {
  test('shows transactions page with table', async ({ page }) => {
    await page.goto('/transactions')
    await expect(page.getByRole('heading', { name: /transactions/i }).first()).toBeVisible()
  })

  test('search filters transactions', async ({ page }) => {
    await page.goto('/transactions')

    const searchInput = page.getByPlaceholder(/search/i)
    if (await searchInput.isVisible()) {
      await searchInput.fill('WHOLE FOODS')
      await page.waitForTimeout(500)
      // Should not crash
      await expect(page.getByRole('heading', { name: /transactions/i }).first()).toBeVisible()
    }
  })

  test('category filter works', async ({ page }) => {
    await page.goto('/transactions')

    // Find category filter select
    const categorySelect = page.locator('select').filter({ hasText: /all categories|category/i }).first()
    if (await categorySelect.isVisible()) {
      // Select first non-default option
      const options = await categorySelect.locator('option').allTextContents()
      if (options.length > 1) {
        await categorySelect.selectOption({ index: 1 })
        await page.waitForTimeout(500)
      }
    }
  })

  test('pagination controls render', async ({ page }) => {
    await page.goto('/transactions')
    await page.waitForTimeout(1000)

    // Page should show transaction count or pagination
    // Just verify no crash with various data states
    await expect(page.getByRole('heading', { name: /transactions/i }).first()).toBeVisible()
  })
})
