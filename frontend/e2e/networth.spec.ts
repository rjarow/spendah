import { test, expect } from '@playwright/test'

test.describe('Net Worth', () => {
  test('shows net worth page with sections', async ({ page }) => {
    await page.goto('/net-worth')
    await expect(page.getByRole('heading', { name: /net worth/i }).first()).toBeVisible()

    // Should show assets and liabilities sections
    await expect(page.getByText(/assets/i).first()).toBeVisible()
    await expect(page.getByText(/liabilities/i).first()).toBeVisible()
  })

  test('displays account balances', async ({ page }) => {
    await page.goto('/net-worth')

    // Should show balance amounts (even if $0)
    await expect(page.getByText(/\$/i).first()).toBeVisible({ timeout: 5000 })
  })

  test('refresh button works', async ({ page }) => {
    await page.goto('/net-worth')

    const refreshBtn = page.getByRole('button', { name: /refresh/i })
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click()
      // Should not crash, page should still be visible
      await expect(page.getByRole('heading', { name: /net worth/i }).first()).toBeVisible()
    }
  })

  test('can update balance from net worth page', async ({ page }) => {
    await page.goto('/net-worth')
    await page.waitForTimeout(1000)

    const updateBtn = page.getByRole('button', { name: /update balance/i }).first()
    if (await updateBtn.isVisible()) {
      await updateBtn.click()

      const input = page.locator('input[type="number"]').first()
      if (await input.isVisible()) {
        await input.fill('10000')
        await page.getByRole('button', { name: /save/i }).first().click()
        await page.waitForTimeout(1000)
      }
    }
  })
})
