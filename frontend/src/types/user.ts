export interface User {
  id: string
  email: string
  display_name: string | null
  avatar_url: string | null
}

export interface WorkspaceMembership {
  workspace_id: string
  role: string
}
