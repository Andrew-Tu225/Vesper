import { Link, useSearchParams } from 'react-router-dom'
import { getAllPosts, getFeaturedPost, getPostsByCategory } from '../content/blog'
import type { BlogCategory } from '../content/blog/types'
import { BlogCard } from '../components/blog/BlogCard'
import { PublicNav } from '../components/layout/PublicNav'
import { useSEO } from '../hooks/useSEO'
import styles from '../components/blog/blog.module.css'

const CATEGORIES: { value: BlogCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'product', label: 'Product' },
  { value: 'playbook', label: 'Playbook' },
  { value: 'field-notes', label: 'Field Notes' },
  { value: 'changelog', label: 'Changelog' },
]

const BLOG_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'Blog',
  name: 'Vesper Blog',
  description: 'Insights on B2B content strategy, AI content tools, and building LinkedIn presence for SaaS founders and GTM teams.',
  url: 'https://tryvesper.vercel.app/blog',
  publisher: {
    '@type': 'Organization',
    name: 'Vesper',
    url: 'https://tryvesper.vercel.app',
    logo: {
      '@type': 'ImageObject',
      url: 'https://tryvesper.vercel.app/logo.svg',
    },
  },
}

export default function BlogIndex() {
  const [params, setParams] = useSearchParams()
  const activeCategory = (params.get('category') ?? 'all') as BlogCategory | 'all'

  useSEO({
    title: 'Blog — AI Content Strategy for B2B Founders',
    description:
      'Insights on B2B content strategy, Slack-driven marketing, and building LinkedIn presence for SaaS founders and GTM teams.',
    canonical: '/blog',
    ogType: 'website',
    jsonLd: BLOG_JSON_LD,
  })

  const featured = getFeaturedPost()
  const showFeatured = activeCategory === 'all' && !!featured

  // When a category is active, show ALL matching posts in the list (including
  // the featured post). When "All" is active, the featured post gets its own
  // hero section and is excluded from the list below.
  const filteredPosts = activeCategory === 'all' ? getAllPosts() : getPostsByCategory(activeCategory)
  const listPosts = showFeatured
    ? filteredPosts.filter(p => p.slug !== featured!.slug)
    : filteredPosts

  function handleCategoryChange(value: BlogCategory | 'all') {
    if (value === 'all') {
      params.delete('category')
    } else {
      params.set('category', value)
    }
    setParams(params, { replace: true })
  }

  return (
    <div className={styles.indexPage}>
      <PublicNav />

      <header className={styles.indexHeader}>
        <h1 className={styles.indexTitle}>Blog</h1>
        <p className={styles.indexSub}>
          Insights on B2B content, AI tools, and building LinkedIn presence for SaaS teams.
        </p>
      </header>

      <div className={styles.indexInner}>
        <div className={styles.categoryFilter} role="group" aria-label="Filter by category">
          {CATEGORIES.map(cat => (
            <button
              key={cat.value}
              className={`${styles.categoryPill} ${activeCategory === cat.value ? styles.categoryPillActive : ''}`}
              onClick={() => handleCategoryChange(cat.value)}
              aria-pressed={activeCategory === cat.value}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {showFeatured && (
          <section className={styles.featuredSection} aria-label="Featured post">
            <BlogCard post={featured!} variant="featured" />
          </section>
        )}

        {listPosts.length > 0 && (
          <section className={styles.recentSection} aria-label="Recent posts">
            {showFeatured && <p className={styles.listLabel}>All posts</p>}
            <div className={styles.postList}>
              {listPosts.map(post => (
                <BlogCard key={post.slug} post={post} />
              ))}
            </div>
          </section>
        )}

        {filteredPosts.length === 0 && (
          <p className={styles.emptyState}>No posts in this category yet.</p>
        )}
      </div>

      <footer className={styles.indexFooter}>
        <p>
          &copy; {new Date().getFullYear()} Vesper &middot;{' '}
          <Link to="/privacy">Privacy</Link> &middot;{' '}
          <Link to="/terms">Terms</Link>
        </p>
      </footer>
    </div>
  )
}