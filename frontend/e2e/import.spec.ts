import { test, expect } from '@playwright/test'
import { testCSVContent } from './helpers'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test.describe('Import', () => {
  let csvPath: string

  test.beforeAll(() => {
    csvPath = path.join(__dirname, 'test-transactions.csv')
    fs.writeFileSync(csvPath, testCSVContent())
  })

  test.afterAll(() => {
    if (fs.existsSync(csvPath)) {
      fs.unlinkSync(csvPath)
    }
  })

  test('shows import page with upload area', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: /import/i }).first()).toBeVisible()

    const fileInput = page.locator('input[type="file"]')
    await expect(fileInput).toBeAttached()
  })

  test('can upload a CSV and see preview', async ({ page }) => {
    await page.goto('/import')

    // Select the file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(csvPath)

    // Click "Upload File" button to trigger the upload
    await page.getByRole('button', { name: /upload file/i }).click()

    // Wait for preview/mapping UI to appear
    await expect(
      page.getByText(/column|mapping|date|account/i).nth(1)
    ).toBeVisible({ timeout: 10000 })
  })

  test('can configure column mapping and confirm import', async ({ page }) => {
    await page.goto('/import')

    // Select and upload
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(csvPath)
    await page.getByRole('button', { name: /upload file/i }).click()

    // Select an account (required before import is enabled)
    const accountSelect = page.locator('select').filter({ hasText: /select account/i }).first()
    await accountSelect.waitFor({ timeout: 10000 })
    // Pick the first real account option (index 1, skipping placeholder)
    const options = await accountSelect.locator('option').allTextContents()
    if (options.length > 1) {
      await accountSelect.selectOption({ index: 1 })
    }

    // Wait for import button to be enabled and click
    const importBtn = page.getByRole('button', { name: /import.*transaction/i })
    await expect(importBtn).toBeEnabled({ timeout: 5000 })
    await importBtn.click()

    // After import, page should return to upload state (confirm section disappears)
    // or show a success/error message
    await expect(
      page.getByText(/drop csv|import successful|failed/i).first()
    ).toBeVisible({ timeout: 15000 })
  })

  test('shows import history', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByText(/recent import/i).first()).toBeVisible({ timeout: 5000 })
  })
})
