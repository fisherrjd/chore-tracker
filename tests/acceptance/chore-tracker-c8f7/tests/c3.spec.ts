import { expect, test } from '@playwright/test'
import { png } from './png'

// jade drives the photo API: upload, fetch, refuse bad input, and cleanup on delete
test('c3 photo API validates and cleans up', async ({ request }) => {
  const tok = Math.random().toString(36).slice(2, 8)
  const L = `Costco-${tok}`
  const enc = encodeURIComponent
  const body = png(10, 20, 30)
  const upload = (list: string, item: string, buffer: Buffer, mimeType = 'image/png', name = 'p.png') =>
    request.put(`/api/lists/${enc(list)}/photo`, { multipart: { item, file: { name, mimeType, buffer } } })
  const find = (j: any, n: string) => j.items.find((i: any) => i.name === n)

  expect((await request.post('/api/lists', { data: { name: L } })).ok()).toBeTruthy()
  const added = await (await request.post(`/api/lists/${enc(L)}/items`, { data: { item: 'Paper towels' } })).json()
  expect(find(added, 'Paper towels')).toHaveProperty('image_url', null)

  const r2 = await upload(L, 'Paper towels', body)
  expect(r2.status()).toBe(200)
  const it = find(await r2.json(), 'Paper towels')
  expect(it.image_url).toMatch(/^\/api\/photos\//)
  expect(it.done).toBe(false)
  const url: string = it.image_url

  const r3 = await request.get(url)
  expect(r3.status()).toBe(200)
  expect(r3.headers()['content-type']).toContain('image/png')
  expect(Buffer.compare(await r3.body(), body)).toBe(0)

  const r4 = await upload(L, 'Paper towels', Buffer.from('hello'), 'text/plain', 'a.txt')
  expect(r4.status()).toBe(415)
  expect((await r4.json()).detail).toMatch(/JPEG|PNG|WebP|GIF/)
  const lists = await (await request.get('/api/lists')).json()
  expect(find(lists.find((l: any) => l.name === L), 'Paper towels').image_url).toBe(url)

  const big = Buffer.concat([body.subarray(0, 8), Buffer.alloc(11 * 1024 * 1024)])
  expect((await upload(L, 'Nope', body)).status()).toBe(404)
  expect((await upload(`NoSuchList-${tok}`, 'Paper towels', big)).status()).toBe(404)
  const r6 = await upload(L, 'Paper towels', big)
  expect(r6.status()).toBe(413)
  expect((await r6.json()).detail).toBe('Photo is too big (max 10 MB)')

  for (const p of ['/api/photos/..%2Fconfig.yaml', '/api/photos/a/b.png', '/api/photos/notaphoto.png']) {
    const r = await request.get(p)
    expect(r.status()).toBe(404)
    expect(typeof (await r.json()).detail).toBe('string')
  }

  const d8 = await request.delete(`/api/lists/${enc(L)}/items/${enc('Paper towels')}`)
  expect(d8.status()).toBe(200)
  expect(find(await d8.json(), 'Paper towels')).toBeUndefined()
  expect((await request.get(url)).status()).toBe(404)

  await request.post(`/api/lists/${enc(L)}/items`, { data: { item: 'Batteries' } })
  const b = find(await (await upload(L, 'Batteries', body)).json(), 'Batteries')
  const d9 = await request.delete(`/api/lists/${enc(L)}/photo/Batteries`)
  expect(d9.status()).toBe(200)
  expect(find(await d9.json(), 'Batteries').image_url).toBeNull()
  expect((await request.get(b.image_url)).status()).toBe(404)

  await request.post(`/api/lists/${enc(L)}/items`, { data: { item: 'Tape' } })
  const t = find(await (await upload(L, 'Tape', body)).json(), 'Tape')
  expect((await request.delete(`/api/lists/${enc(L)}`)).ok()).toBeTruthy()
  expect((await request.get(t.image_url)).status()).toBe(404)
})
