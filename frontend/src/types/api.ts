export interface DraftPost {
  id: string
  variant_number: number
  body: string
  is_selected: boolean
  feedback: string | null
  scheduled_at: string | null
  published_at: string | null
  created_at: string
}

export interface SignalListItem {
  id: string
  signal_type: string | null
  summary: string | null
  status: string
  source_type: string
  source_channel: string | null
  created_at: string
}

export interface SignalListResponse {
  signals: SignalListItem[]
  total: number
  page: number
  limit: number
}

export interface SignalDetail extends SignalListItem {
  draft_posts: DraftPost[]
}

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: string | null
}

export interface ApiError {
  message: string
  status: number
}

export class FetchError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message)
    this.name = 'FetchError'
  }
}
