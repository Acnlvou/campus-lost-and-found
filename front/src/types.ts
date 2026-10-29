export interface User {
  id: number
  username: string
  name: string
  role: string
}

export interface Item {
  id: number
  owner_id: number
  kind: string
  title: string
  category: string
  location: string
  event_time: string
  description: string
  status: string
  pub_status: string
  created_at: string
  owner_name?: string
  review_reason?: string
}

export interface Claim {
  id: number
  item_id: number
  applicant_id: number
  note: string
  status: string
  created_at: string
  updated_at: string
  applicant_name?: string
  title?: string
  location?: string
}

export interface AuditRow {
  id: number
  actor_id: number | null
  action: string
  item_id: number | null
  detail: string
  created_at: string
}

export interface SessionData {
  user: User | null
  csrf: string
  is_admin: boolean
  version: string
  allow_self: boolean
  categories: string[]
  labels: Record<string, string>
}

export interface DetailData {
  item: Item
  owner: boolean
  is_admin: boolean
  claims: Claim[]
  history: AuditRow[]
}
