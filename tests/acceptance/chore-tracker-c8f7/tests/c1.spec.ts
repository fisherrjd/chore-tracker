import { expect, test } from '@playwright/test'
import { png } from './png'

// jade adds an item with an attached photo; thumbnail shows and survives a reload
test('c1 add an item with a photo', async ({ page }) => {
  const name = `Groceries-${Math.random().toString(36).slice(2, 8)}`
  await page.goto('/lists')
  await page.getByPlaceholder('List name (e.g. Costco, Kroger, Target)').fill(name)
  await page.getByRole('button', { name: 'Add list' }).click()
  const card = () =>
    page.locator('div').filter({ hasText: name }).filter({ has: page.getByPlaceholder('Add an item…') }).last()
  await expect(card()).toBeVisible()

  await card().getByPlaceholder('Add an item…').fill('Oat milk')
  const chooser = page.waitForEvent('filechooser')
  await card().getByRole('button', { name: 'Attach a photo' }).click()
  await (await chooser).setFiles({ name: 'milk.png', mimeType: 'image/png', buffer: png(200, 30, 30) })
  await expect(card().getByText('Photo attached')).toBeVisible()
  await card().getByRole('button', { name: 'Add', exact: true }).click()

  const thumb = () => card().getByRole('button', { name: 'View photo of Oat milk' }).getByRole('img', { name: 'Oat milk' })
  await expect(thumb()).toBeVisible()
  await expect.poll(() => thumb().evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0)
  await expect(card().getByText('Photo attached')).toHaveCount(0)
  await expect(card().getByPlaceholder('Add an item…')).toHaveValue('')

  await card().getByPlaceholder('Add an item…').fill('Dish soap')
  await card().getByRole('button', { name: 'Add', exact: true }).click()
  await expect(card().getByRole('button', { name: 'Add photo to Dish soap' })).toBeVisible()
  await expect(card().getByRole('button', { name: 'View photo of Dish soap' })).toHaveCount(0)

  await page.reload()
  await expect(thumb()).toBeVisible()
  expect(await thumb().getAttribute('src')).toMatch(/^\/api\/photos\//)
})
