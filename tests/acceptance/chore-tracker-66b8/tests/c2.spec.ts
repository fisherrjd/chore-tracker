import { expect, test } from '@playwright/test'
import { clearTicks, reset, seed } from './helpers'

const ROOMS: Record<string, string[]> = {
  Kitchen: ['Dishes', 'Fridge', 'Oven', 'Floor'],
  Bathroom: ['Toilet', 'Sink'],
  'Living Room': ['Dust', 'Vacuum'],
  Bedroom: ['Dust', 'Sheets'],
  Office: ['Dust'],
}
const DUST = ['Living Room', 'Bedroom', 'Office']

// Jade ticks Dust in one room and a task in another during a full clean; only those stick, matching Today.
test('c2 tick tasks across rooms', async ({ page, request }) => {
  await reset(request)
  await seed(request, ['Jade', 'Hannah'], ROOMS)
  await clearTicks(request, ['Jade', 'Hannah'], Object.keys(ROOMS))
  const started = await request.post('/api/full-clean')
  expect(started.status()).toBe(200)

  const home = await (await request.get('/api/home')).json()
  const split: Record<string, string[]> = home.full_clean_rooms
  const member = Object.keys(split).find((m) => split[m].filter((r) => DUST.includes(r)).length >= 2)!
  expect(member).toBeTruthy()
  const mine = split[member]
  const dust = mine.filter((r) => DUST.includes(r))
  const d2 = dust.find((r) => r !== 'Office')!
  const d1 = dust.find((r) => r !== d2)!
  const other = mine.find((r) => r !== d1 && r !== d2) ?? d2
  const otherTask = ROOMS[other].find((t) => t !== 'Dust')!
  const total = mine.reduce((n, r) => n + ROOMS[r].length, 0)

  await page.goto(`/checklist/${member}`)
  await expect(page.getByText(`Full house clean · ${mine.length} rooms`)).toBeVisible()
  for (const r of mine) await expect(page.getByRole('heading', { name: r })).toBeVisible()

  const section = (room: string) =>
    page
      .getByRole('heading', { name: room })
      .locator('xpath=ancestor::*[.//*[@role="checkbox"]][1]')

  const saved = page.waitForResponse((res) => {
    if (res.request().method() !== 'POST' || !res.url().includes('/api/checklist/')) return false
    const body = res.request().postDataJSON() as { rooms?: Record<string, string[]> }
    const n = Object.values(body.rooms ?? {}).reduce((s, l) => s + l.length, 0)
    return n === 2
  })
  await section(d1).getByRole('checkbox', { name: 'Dust' }).click()
  await section(other).getByRole('checkbox', { name: otherTask, exact: true }).click()
  await saved

  await page.reload()
  await expect(page.getByText(`${2}/${total} done across all rooms`)).toBeVisible()
  await expect(section(d1).getByRole('checkbox', { name: 'Dust' })).toBeChecked()
  await expect(section(d2).getByRole('checkbox', { name: 'Dust' })).not.toBeChecked()
  await expect(section(other).getByRole('checkbox', { name: otherTask, exact: true })).toBeChecked()

  await page.goto('/')
  await expect(page.getByRole('link', { name: new RegExp(member) })).toContainText(`2/${total} done`)
})
