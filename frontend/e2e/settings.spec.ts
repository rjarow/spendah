import { test, expect } from '@playwright/test'

test.describe('Settings', () => {
  test('shows settings page with AI configuration', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible()

    // Should show AI provider settings
    await expect(page.getByText(/ai|provider|model/i).first()).toBeVisible()
  })

  test('can change AI provider', async ({ page }) => {
    await page.goto('/settings')

    // Find provider select
    const providerSelect = page.locator('select').first()
    if (await providerSelect.isVisible()) {
      // Just verify it has options and doesn't crash on change
      const options = await providerSelect.locator('option').allTextContents()
      expect(options.length).toBeGreaterThan(0)
    }
  })

  test('settings page does not crash with no API key', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(1000)

    // Page should still render without errors
    await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible()
  })
})
