import type { BlogPost, BlogCategory } from './types'
import introducingVesper from './posts/introducing-vesper'

const ALL_POSTS: BlogPost[] = [introducingVesper].sort(
  (a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
)

export function getAllPosts(): BlogPost[] {
  return ALL_POSTS
}

export function getPostsByCategory(category: BlogCategory): BlogPost[] {
  return ALL_POSTS.filter(p => p.category === category)
}

export function getPostBySlug(slug: string): BlogPost | null {
  return ALL_POSTS.find(p => p.slug === slug) ?? null
}

export function getFeaturedPost(): BlogPost | null {
  return ALL_POSTS.find(p => p.featured) ?? ALL_POSTS[0] ?? null
}

export function getRecentPosts(excludeSlug?: string, limit = 6): BlogPost[] {
  return ALL_POSTS.filter(p => p.slug !== excludeSlug).slice(0, limit)
}