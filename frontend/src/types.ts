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
}

export interface MembersData {
  members: Member[]
  ntfy_base_url: string
}

export interface SettingsData {
  notify_times: string[]
  timezone: string
}

export interface ChecklistData {
  member: string
  room_name: string | null
  tasks: string[]
  done: string[]
}

export interface NotifyResult {
  sent: string[]
  failed: string[]
}
