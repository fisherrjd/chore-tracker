import { expect, test } from '@playwright/test'
import { png } from './png'

// jade buys an item with a photo and clears bought; its photo goes, others stay
test('c4 clearing bought items drops their photos', async ({ page, request }) => {
  const name = `Groceries-${Math.random().toString(36).slice(2, 8)}`
  await page.goto('/lists')
  await page.getByPlaceholder('List name (e.g. Costco, Kroger, Target)').fill(name)
  await page.getByRole('button', { name: 'Add list' }).click()
  const card = () =>
    page.locator('div').filter({ hasText: name }).filter({ has: page.getByPlaceholder('Add an item…') }).last()
  await expect(card()).toBeVisible()

  const addWithPhoto = async (item: string, color: [number, number, number]) => {
    await card().getByPlaceholder('Add an item…').fill(item)
    const chooser = page.waitForEvent('filechooser')
    await card().getByRole('button', { name: 'Attach a photo' }).click()
    await (await chooser).setFiles({ name: `${item}.png`, mimeType: 'image/png', buffer: png(...color) })
    await expect(card().getByText('Photo attached')).toBeVisible()
    await card().getByRole('button', { name: 'Add', exact: true }).click()
    await expect(card().getByRole('button', { name: `View photo of ${item}` })).toBeVisible()
  }
  await addWithPhoto('Eggs', [250, 250, 200])
  await addWithPhoto('Bread', [150, 100, 50])

  const thumb = (item: string) => card().getByRole('button', { name: `View photo of ${item}` }).getByRole('img', { name: item })
  const eggsSrc = (await thumb('Eggs').getAttribute('src'))!
  const breadSrc = (await thumb('Bread').getAttribute('src'))!

  await card().getByRole('checkbox', { name: 'Eggs' }).click()
  await expect(thumb('Eggs')).toBeVisible()

  await card().getByRole('button', { name: 'Clear 1 bought' }).click()
  await expect(page.getByText(`Cleared 1 bought item from ${name}`)).toBeVisible()
  await expect(card().getByRole('checkbox', { name: 'Eggs' })).toHaveCount(0)

  expect((await request.get(eggsSrc)).status()).toBe(404)
  expect((await request.get(breadSrc)).status()).toBe(200)

  await page.reload()
  await expect(thumb('Bread')).toBeVisible()
  await expect.poll(() => thumb('Bread').evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0)
})
