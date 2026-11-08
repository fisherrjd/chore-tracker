import { expect, test } from '@playwright/test'
import { clearTicks, reset, seed } from './helpers'

const ROOMS = {
  Kitchen: ['Dishes', 'Fridge', 'Oven', 'Floor'],
  Bathroom: ['Toilet', 'Sink'],
  'Living Room': ['Dust', 'Vacuum'],
  Bedroom: ['Dust', 'Sheets'],
  Office: ['Dust'],
}

// Jade taps Full house clean, confirms, and every room lands on exactly one of the two cards.
test('c1 start a full house clean', async ({ page, request }) => {
  await reset(request)
  await seed(request, ['Jade', 'Hannah'], ROOMS)
  await clearTicks(request, ['Jade', 'Hannah'], Object.keys(ROOMS))

  await page.goto('/')
  await expect(page.getByRole('link', { name: /Jade/ })).toBeVisible()
  await page.getByRole('button', { name: 'Full house clean', exact: true }).click()

  await expect(page.getByText('Start a full house clean?')).toBeVisible()
  await expect(page.getByText(/split between (Jade and Hannah|Hannah and Jade)/)).toBeVisible()
  await page.getByRole('button', { name: 'Start full clean' }).click()

  await expect(page.getByText('Full house clean started')).toBeVisible()
  await expect(page.getByText('Full house clean today')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Back to normal' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Full house clean', exact: true })).toHaveCount(0)

  const jade = page.getByRole('link', { name: /Jade/ })
  const hannah = page.getByRole('link', { name: /Hannah/ })
  await expect(jade).toContainText(/\d+ rooms/)
  await expect(hannah).toContainText(/\d+ rooms/)
  const texts = [(await jade.textContent()) ?? '', (await hannah.textContent()) ?? '']

  for (const room of Object.keys(ROOMS)) {
    expect(texts.filter((t) => t.includes(room)), room).toHaveLength(1)
  }

  const totals = texts.map((t) => {
    const m = t.match(/0\/(\d+) done/)
    expect(m).not.toBeNull()
    return Number(m![1])
  })
  expect(totals[0] + totals[1]).toBe(11)
  expect(Math.abs(totals[0] - totals[1])).toBeLessThanOrEqual(4)

  await page.reload()
  await expect(page.getByText('Full house clean today')).toBeVisible()
})
