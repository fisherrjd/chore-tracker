import type {
  ChecklistData,
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
  const r = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!r.ok) {
    const body = await r.json().catch(() => ({ detail: r.statusText }))
    throw new ApiError(r.status, (body as { detail?: string }).detail ?? r.statusText)
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
  clearBought: (list: string) =>
    req<ShoppingList & { removed: number }>(`/api/lists/${encodeURIComponent(list)}/clear`, {
      method: 'POST',
    }),
}
