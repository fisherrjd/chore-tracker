import { expect, test } from '@playwright/test'
import { reset, seed } from './helpers'

// Jade taps Back to normal and Today shows one room each again with the rotation unchanged.
test('c3 back to normal', async ({ page, request }) => {
  await reset(request)
  await seed(request, ['Jade', 'Hannah'], {
    Kitchen: ['Tidy'],
    Bathroom: ['Tidy'],
    'Living Room': ['Tidy'],
    Bedroom: ['Tidy'],
  })

  const rows = page.getByRole('row')
  const rotation = async () => (await rows.allInnerTexts()).slice(2)
  const cards = async () => [
    await page.getByRole('link', { name: /Jade/ }).innerText(),
    await page.getByRole('link', { name: /Hannah/ }).innerText(),
  ]

  await page.goto('/')
  await expect(rows).toHaveCount(15)
  const rotationBefore = await rotation()
  const cardsBefore = await cards()

  await page.getByRole('button', { name: 'Full house clean', exact: true }).click()
  await page.getByRole('button', { name: 'Start full clean' }).click()
  await expect(page.getByText('Full house clean today')).toBeVisible()
  expect(await rotation()).toEqual(rotationBefore)

  await page.getByRole('button', { name: 'Back to normal' }).click()
  await expect(page.getByText('Back to the normal rotation')).toBeVisible()
  await expect(page.getByText('Full house clean today')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Full house clean', exact: true })).toBeVisible()

  expect(await cards()).toEqual(cardsBefore)
  expect(await rotation()).toEqual(rotationBefore)
})
