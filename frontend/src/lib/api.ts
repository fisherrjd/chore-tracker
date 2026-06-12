import type {
  ChecklistData,
  HomeData,
  MembersData,
  NotifyResult,
  Room,
  Member,
  SettingsData,
} from '@/types'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
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
}
