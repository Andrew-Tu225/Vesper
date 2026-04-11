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
