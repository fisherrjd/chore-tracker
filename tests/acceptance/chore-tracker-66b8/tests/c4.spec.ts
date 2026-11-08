import { expect, test } from '@playwright/test'
import { clearTicks, reset, seed } from './helpers'

const ROOMS: Record<string, string[]> = {
  A: ['a1', 'a2', 'a3'],
  B: ['b1'],
  C: ['c1', 'c2'],
  D: ['d1'],
  E: ['e1', 'e2'],
  F: ['x'],
}
type Rooms = { name: string; tasks: string[]; done: string[] }[]

// Start and stop a full clean via the API; only today changes, the split stays put, earlier ticks are kept.
test('c4 full clean API', async ({ request }) => {
  await reset(request)

  // 1
  const empty = await request.post('/api/full-clean')
  expect(empty.status()).toBe(409)
  expect((await empty.json()).detail).toBe('Add rooms and members first')

  // 2
  await seed(request, ['Jade', 'Hannah'], ROOMS)
  await clearTicks(request, ['Jade', 'Hannah'], Object.keys(ROOMS))

  // 3
  const home0 = await (await request.get('/api/home')).json()
  const schedule0 = home0.schedule
  const jade0 = await (await request.get('/api/checklist/Jade')).json()
  const N: string = jade0.room_name
  const K: string = jade0.tasks[0]
  expect((await request.post('/api/checklist/Jade', { data: { tasks: [K] } })).status()).toBe(200)

  // 4
  const start = await request.post('/api/full-clean')
  expect(start.status()).toBe(200)
  const s = await start.json()
  expect(s.active).toBe(true)
  expect(Object.keys(s.assignments).sort()).toEqual(['Hannah', 'Jade'])
  expect((Object.values(s.assignments) as string[][]).flat().sort()).toEqual(Object.keys(ROOMS))
  expect(s.sent).toEqual([])
  expect(s.failed).toEqual([])

  // 5
  const home1 = await (await request.get('/api/home')).json()
  expect(home1.full_clean).toBe(true)
  expect(home1.full_clean_rooms).toEqual(s.assignments)
  expect(home1.schedule).toEqual(schedule0)
  expect(await (await request.get('/api/schedule')).json()).toEqual(schedule0)
  const holder = Object.keys(s.assignments).find((m) => s.assignments[m].includes(N))!
  for (const m of ['Jade', 'Hannah']) {
    const c = await (await request.get(`/api/checklist/${m}`)).json()
    expect(c.full_clean).toBe(true)
    expect((c.rooms as Rooms).map((r) => r.name).sort()).toEqual([...s.assignments[m]].sort())
    if (m === holder) {
      expect((c.rooms as Rooms).find((r) => r.name === N)!.done).toContain(K)
    }
  }

  // 6
  const again = await request.post('/api/full-clean')
  expect(again.status()).toBe(200)
  const a = await again.json()
  expect(a.active).toBe(true)
  expect(a.assignments).toEqual(s.assignments)
  expect(a.sent).toEqual([])
  expect(a.failed).toEqual([])
  expect((await request.post('/api/rooms/A/tasks', { data: { task: 'a4' } })).ok()).toBe(true)
  expect((await request.post('/api/settings/notify-times', { data: { time: '06:30' } })).ok()).toBe(true)
  const home2 = await (await request.get('/api/home')).json()
  expect(home2.full_clean).toBe(true)
  expect(home2.full_clean_rooms).toEqual(s.assignments)

  // 7
  const jadeFc = await (await request.get('/api/checklist/Jade')).json()
  const R = (jadeFc.rooms as Rooms).find((r) => r.name !== N)!
  const post = await request.post('/api/checklist/Jade', { data: { rooms: { [R.name]: [R.tasks[0]] } } })
  expect(post.status()).toBe(200)
  expect(Array.isArray((await post.json()).rooms)).toBe(true)
  const jade2 = (await (await request.get('/api/checklist/Jade')).json()).rooms as Rooms
  for (const r of jade2) {
    expect(r.done.includes(R.tasks[0]), r.name).toBe(r.name === R.name)
  }
  const holder2 = await (await request.get(`/api/checklist/${holder}`)).json()
  expect((holder2.rooms as Rooms).find((r) => r.name === N)!.done).toContain(K)

  // 8
  expect((await request.post('/api/checklist/Jade', { data: {} })).status()).toBe(422)

  // 9
  const stop = await request.delete('/api/full-clean')
  expect(stop.status()).toBe(200)
  expect(await stop.json()).toEqual({ active: false })
  const home3 = await (await request.get('/api/home')).json()
  expect(home3.full_clean).toBe(false)
  expect(home3.full_clean_rooms).toEqual({})
  expect(home3.schedule).toEqual(schedule0)
  const jade3 = await (await request.get('/api/checklist/Jade')).json()
  expect(jade3.full_clean).toBe(false)
  expect(jade3.rooms).toHaveLength(1)
  expect(jade3.done).toContain(K)
})
