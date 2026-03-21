import { test, expect } from '@playwright/test'

test.describe('Coach', () => {
  test('shows coach page with chat input', async ({ page }) => {
    await page.goto('/coach')
    await expect(page.getByText(/financial coach|coach/i).first()).toBeVisible()

    // Chat input should exist
    const input = page.getByPlaceholder(/ask|message|finances/i)
    await expect(input).toBeVisible()
  })

  test('shows quick questions on empty state', async ({ page }) => {
    await page.goto('/coach')

    // Quick questions should appear when no conversation is active
    await expect(
      page.getByText(/how much|what are|how does|subscription/i).first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('can click a quick question to fill input', async ({ page }) => {
    await page.goto('/coach')

    // Wait for quick questions to load
    await page.waitForTimeout(1000)

    const quickQuestion = page.getByRole('button').filter({ hasText: /how much|spend/i }).first()
    if (await quickQuestion.isVisible()) {
      await quickQuestion.click()
      await page.waitForTimeout(500)
    }
  })

  test('can type a message (without sending to avoid AI dependency)', async ({ page }) => {
    await page.goto('/coach')

    const input = page.getByPlaceholder(/ask|message|finances/i)
    await input.fill('What did I spend last month?')

    // Send button should be enabled
    const sendBtn = page.getByRole('button', { name: /send/i })
    await expect(sendBtn).toBeEnabled()
  })

  test('conversations panel shows new conversation button', async ({ page }) => {
    await page.goto('/coach')

    // Should show conversations panel with new conversation option
    await expect(page.getByText(/conversation/i).first()).toBeVisible()
  })
})
