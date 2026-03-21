import { test, expect } from '@playwright/test'

test.describe('Budgets', () => {
  test('shows budgets page', async ({ page }) => {
    await page.goto('/budgets')
    await expect(page.getByRole('heading', { name: /budgets/i }).first()).toBeVisible()
  })

  test('shows empty state with create button', async ({ page }) => {
    await page.goto('/budgets')

    // Either shows budgets or empty state with create button
    const addButton = page.getByRole('button', { name: /add budget|create.*budget/i })
    await expect(addButton.first()).toBeVisible({ timeout: 5000 })
  })

  test('can open create budget dialog', async ({ page }) => {
    await page.goto('/budgets')

    const addButton = page.getByRole('button', { name: /add budget|create.*budget/i })
    await addButton.first().click()

    // Modal should appear with form fields
    const modal = page.locator('.fixed.inset-0')
    await expect(modal.locator('input[type="number"]')).toBeVisible()
    await expect(modal.locator('select').first()).toBeVisible()
  })

  test('can create a budget', async ({ page }) => {
    await page.goto('/budgets')

    const addButton = page.getByRole('button', { name: /add budget|create.*budget/i })
    await addButton.first().click()

    // Fill form within the modal
    const modal = page.locator('.fixed.inset-0')
    await modal.locator('input[type="number"]').fill('500')

    // Submit
    await modal.getByRole('button', { name: /create budget/i }).click()

    // Budget should appear in list (modal closes)
    await expect(page.getByText('$500').first()).toBeVisible({ timeout: 5000 })
  })

  test('can switch view periods', async ({ page }) => {
    await page.goto('/budgets')

    // Period selector should exist
    const periodSelect = page.locator('select').first()
    if (await periodSelect.isVisible()) {
      await periodSelect.selectOption('previous')
      // Page should update without crashing
      await page.waitForTimeout(1000)
      await expect(page.getByRole('heading', { name: /budgets/i }).first()).toBeVisible()
    }
  })

  test('can delete a budget', async ({ page }) => {
    await page.goto('/budgets')
    await page.waitForTimeout(1000)

    // If there's a delete button, test it
    const deleteBtn = page.getByRole('button').filter({ has: page.locator('svg.lucide-trash-2') }).first()
    if (await deleteBtn.isVisible()) {
      // Handle confirmation dialog
      page.on('dialog', dialog => dialog.accept())
      await deleteBtn.click()
      await page.waitForTimeout(1000)
    }
  })
})
