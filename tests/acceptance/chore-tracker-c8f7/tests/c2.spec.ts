import { expect, test } from '@playwright/test'
import { png } from './png'

// jade adds a photo to an existing item, opens it, replaces it, then removes it
test('c2 photo on an existing item: add, view, replace, remove', async ({ page, request }) => {
  const name = `Groceries-${Math.random().toString(36).slice(2, 8)}`
  await page.goto('/lists')
  await page.getByPlaceholder('List name (e.g. Costco, Kroger, Target)').fill(name)
  await page.getByRole('button', { name: 'Add list' }).click()
  const card = () =>
    page.locator('div').filter({ hasText: name }).filter({ has: page.getByPlaceholder('Add an item…') }).last()
  await expect(card()).toBeVisible()
  await card().getByPlaceholder('Add an item…').fill('Dish soap')
  await card().getByRole('button', { name: 'Add', exact: true }).click()

  let chooser = page.waitForEvent('filechooser')
  await card().getByRole('button', { name: 'Add photo to Dish soap' }).click()
  await (await chooser).setFiles({ name: 'red.png', mimeType: 'image/png', buffer: png(255, 0, 0) })
  await expect(page.getByText('Photo added to Dish soap')).toBeVisible()

  await card().getByRole('button', { name: 'View photo of Dish soap' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Dish soap', { exact: true })).toBeVisible()
  await expect(dialog.getByText(`On ${name}`)).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Replace photo' })).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Remove photo' })).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Close' }).first()).toBeVisible()
  const img = dialog.getByRole('img', { name: 'Dish soap' })
  await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0)
  const oldSrc = (await img.getAttribute('src'))!

  chooser = page.waitForEvent('filechooser')
  await dialog.getByRole('button', { name: 'Replace photo' }).click()
  await (await chooser).setFiles({ name: 'blue.png', mimeType: 'image/png', buffer: png(0, 0, 255) })
  await expect(page.getByText('Photo replaced on Dish soap')).toBeVisible()
  await expect(dialog).toBeVisible()
  await expect(img).not.toHaveAttribute('src', oldSrc)
  await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0)
  expect((await request.get(oldSrc)).status()).toBe(404)

  await dialog.getByRole('button', { name: 'Remove photo' }).click()
  await expect(page.getByText('Photo removed from Dish soap')).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(card().getByRole('button', { name: 'Add photo to Dish soap' })).toBeVisible()
})
