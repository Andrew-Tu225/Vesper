export type BlogCategory = 'product' | 'playbook' | 'field-notes' | 'changelog'

export interface BlogAuthor {
  name: string
  role: string
  avatarUrl?: string
}

export interface BlogSEO {
  title?: string
  description?: string
  ogImage?: string
  keywords?: string[]
}

export type BlogBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'heading'; level: 2 | 3; text: string }
  | { type: 'pullquote'; text: string; attribution?: string }
  | { type: 'list'; style: 'bulleted' | 'numbered'; items: string[] }
  | { type: 'callout'; tone: 'info' | 'insight' | 'warning'; text: string }
  | { type: 'divider' }

export interface BlogPost {
  slug: string
  title: string
  subtitle?: string
  category: BlogCategory
  author: BlogAuthor
  publishedAt: string
  updatedAt?: string
  readingMinutes: number
  excerpt: string
  eyebrow?: string
  featured?: boolean
  seo?: BlogSEO
  body: BlogBlock[]
}