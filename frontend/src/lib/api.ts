import type {
  ChecklistData,
  ChecklistSaved,
  FullCleanResult,
  HomeData,
  MembersData,
  Member,
  NotifyResult,
  Room,
  SettingsData,
  ShoppingList,
} from '@/types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  // FormData bodies need the browser to set the multipart Content-Type itself.
  const isForm = options?.body instanceof FormData
  const r = await fetch(url, {
    ...(isForm ? {} : { headers: { 'Content-Type': 'application/json' } }),
    ...options,
  })
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    const detail = (body as { detail?: string } | null)?.detail
    if (r.status === 413 && !detail) throw new ApiError(413, 'Photo is too big for the server')
    throw new ApiError(r.status, detail ?? r.statusText)
  }
  return r.json() as Promise<T>
}

export const api = {
  home: () => req<HomeData>('/api/home'),

  rooms: () => req<Room[]>('/api/rooms'),
  addRoom: (name: string) =>
    req<Room>('/api/rooms', { method: 'POST', body: JSON.stringify({ name }) }),
  deleteRoom: (name: string) =>
    req<{ detail: string }>(`/api/rooms/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  addTask: (room: string, task: string) =>
    req<{ task: string }>(`/api/rooms/${encodeURIComponent(room)}/tasks`, {
      method: 'POST',
      body: JSON.stringify({ task }),
    }),
  deleteTask: (room: string, task: string) =>
    req<{ detail: string }>(
      `/api/rooms/${encodeURIComponent(room)}/tasks/${encodeURIComponent(task)}`,
      { method: 'DELETE' },
    ),

  members: () => req<MembersData>('/api/members'),
  addMember: (name: string) =>
    req<Member>('/api/members', { method: 'POST', body: JSON.stringify({ name }) }),
  deleteMember: (name: string) =>
    req<{ detail: string }>(`/api/members/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  settings: () => req<SettingsData>('/api/settings'),
  addNotifyTime: (time: string) =>
    req<{ notify_times: string[] }>('/api/settings/notify-times', {
      method: 'POST',
      body: JSON.stringify({ time }),
    }),
  deleteNotifyTime: (time: string) =>
    req<{ notify_times: string[] }>(
      `/api/settings/notify-times/${encodeURIComponent(time)}`,
      { method: 'DELETE' },
    ),

  checklist: (member: string) =>
    req<ChecklistData>(`/api/checklist/${encodeURIComponent(member)}`),
  updateChecklist: (member: string, tasks: string[]) =>
    req<{ member: string; done: string[] }>(`/api/checklist/${encodeURIComponent(member)}`, {
      method: 'POST',
      body: JSON.stringify({ tasks }),
    }),

  updateChecklistRooms: (member: string, rooms: Record<string, string[]>) =>
    req<ChecklistSaved>(`/api/checklist/${encodeURIComponent(member)}`, {
      method: 'POST',
      body: JSON.stringify({ rooms }),
    }),

  startFullClean: () => req<FullCleanResult>('/api/full-clean', { method: 'POST' }),
  stopFullClean: () => req<FullCleanResult>('/api/full-clean', { method: 'DELETE' }),

  notifyToday: () => req<NotifyResult>('/api/notify/today', { method: 'POST' }),

  lists: () => req<ShoppingList[]>('/api/lists'),
  addList: (name: string) =>
    req<ShoppingList>('/api/lists', { method: 'POST', body: JSON.stringify({ name }) }),
  deleteList: (name: string) =>
    req<{ detail: string }>(`/api/lists/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  addListItem: (list: string, item: string) =>
    req<ShoppingList>(`/api/lists/${encodeURIComponent(list)}/items`, {
      method: 'POST',
      body: JSON.stringify({ item }),
    }),
  setListItem: (list: string, item: string, done: boolean) =>
    req<ShoppingList>(`/api/lists/${encodeURIComponent(list)}/items`, {
      method: 'PUT',
      body: JSON.stringify({ item, done }),
    }),
  deleteListItem: (list: string, item: string) =>
    req<ShoppingList>(
      `/api/lists/${encodeURIComponent(list)}/items/${encodeURIComponent(item)}`,
      { method: 'DELETE' },
    ),
  setListPhoto: (list: string, item: string, file: Blob, filename: string) => {
    const form = new FormData()
    form.append('item', item)
    form.append('file', file, filename)
    return req<ShoppingList>(`/api/lists/${encodeURIComponent(list)}/photo`, {
      method: 'PUT',
      body: form,
    })
  },
  removeListPhoto: (list: string, item: string) =>
    req<ShoppingList>(
      `/api/lists/${encodeURIComponent(list)}/photo/${encodeURIComponent(item)}`,
      { method: 'DELETE' },
    ),
  clearBought: (list: string) =>
    req<ShoppingList & { removed: number }>(`/api/lists/${encodeURIComponent(list)}/clear`, {
      method: 'POST',
    }),
}
