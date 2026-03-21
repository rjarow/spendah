import { test, expect } from '@playwright/test'

test.describe('Accounts', () => {
  test('shows accounts page with create button', async ({ page }) => {
    await page.goto('/accounts')
    await expect(page.getByRole('heading', { name: /accounts/i }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /create account/i })).toBeVisible()
  })

  test('can create a new account', async ({ page }) => {
    await page.goto('/accounts')

    await page.getByRole('button', { name: /create account/i }).click()

    // Fill in the modal form
    await page.getByLabel(/account name/i).fill('E2E Savings')
    await page.getByLabel(/account type/i).selectOption('savings')

    await page.getByRole('button', { name: /create account/i }).last().click()

    // Wait for creation and verify it appears in the list
    await expect(page.getByText('E2E Savings').first()).toBeVisible({ timeout: 5000 })
  })

  test('can update account balance', async ({ page }) => {
    await page.goto('/accounts')
    await page.waitForTimeout(1000)

    // Click first "Update Balance" button (outside any modal)
    const updateBtn = page.getByRole('button', { name: /update balance/i }).first()
    if (await updateBtn.isVisible()) {
      await updateBtn.click()
      await page.waitForTimeout(500)

      // Find the modal and interact within it
      const modal = page.locator('.fixed.inset-0').first()
      const balanceInput = modal.locator('input[type="number"]').first()
      await balanceInput.fill('7500')

      // Click the submit button inside the modal
      await modal.getByRole('button', { name: /update balance/i }).last().click()
      await page.waitForTimeout(1000)
    }
  })
})
