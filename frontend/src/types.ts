export interface Room {
  name: string
  tasks: string[]
}

export interface Member {
  name: string
  topic: string
  ntfy_url: string
}

export interface ScheduleDay {
  date: string
  assignments: Record<string, string>
}

export interface DoneProgress {
  done: number
  total: number
}

export interface HomeData {
  schedule: ScheduleDay[]
  today_idx: number
  half_cycle: number
  notify_times: string[]
  done_map: Record<string, DoneProgress>
  full_clean: boolean
  full_clean_rooms: Record<string, string[]>
}

export interface MembersData {
  members: Member[]
  ntfy_base_url: string
}

export interface SettingsData {
  notify_times: string[]
  timezone: string
}

export interface ChecklistRoom {
  name: string
  tasks: string[]
  done: string[]
}

export interface ChecklistData {
  member: string
  room_name: string | null
  tasks: string[]
  done: string[]
  full_clean: boolean
  rooms: ChecklistRoom[]
}

export interface ChecklistSaved {
  member: string
  full_clean: boolean
  done: string[]
  rooms: ChecklistRoom[]
}

export interface NotifyResult {
  sent: string[]
  failed: string[]
}

export interface FullCleanResult {
  active: boolean
  assignments: Record<string, string[]>
  sent: string[]
  failed: string[]
}

export interface ListItem {
  name: string
  done: boolean
  image_url: string | null
}

export interface ShoppingList {
  name: string
  items: ListItem[]
  remaining: number
  bought: number
}
