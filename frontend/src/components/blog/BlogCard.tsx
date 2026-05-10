import { Link } from 'react-router-dom'
import type { BlogPost } from '../../content/blog/types'
import { blogPostHref } from '../../lib/constants'
import styles from './blog.module.css'

interface BlogCardProps {
  post: BlogPost
  variant?: 'featured' | 'default'
}

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

function longDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function BlogCard({ post, variant = 'default' }: BlogCardProps) {
  const href = blogPostHref(post.slug)
  const label = (post.eyebrow ?? post.category).replace('-', ' ')

  if (variant === 'featured') {
    return (
      <article className={styles.featuredCard}>
        <div className={styles.featuredCardTop}>
          <span className={styles.featuredBadge}>Featured</span>
          <span className={styles.featuredCardMeta}>
            <span className={styles.cardEyebrow}>{label}</span>
            <span className={styles.metaDot} aria-hidden="true" />
            <span>{post.readingMinutes} min read</span>
          </span>
        </div>
        <h2 className={styles.featuredCardTitle}>
          <Link to={href} className={styles.cardTitleLink}>
            {post.title}
          </Link>
        </h2>
        {(post.subtitle ?? post.excerpt) && (
          <p className={styles.featuredCardSubtitle}>{post.subtitle ?? post.excerpt}</p>
        )}
        <div className={styles.featuredCardFooter}>
          <span className={styles.featuredCardAuthor}>
            {post.author.name} &middot;{' '}
            <time dateTime={post.publishedAt}>{longDate(post.publishedAt)}</time>
          </span>
          <Link to={href} className={styles.cardReadMore} aria-label={`Read ${post.title}`}>
            Read post <ArrowRight />
          </Link>
        </div>
      </article>
    )
  }

  return (
    <article className={styles.card}>
      <div className={styles.cardLeft}>
        <time className={styles.cardDate} dateTime={post.publishedAt}>
          {shortDate(post.publishedAt)}
        </time>
      </div>
      <div className={styles.cardRight}>
        <div className={styles.cardTopMeta}>
          <span className={styles.cardEyebrow}>{label}</span>
          <span className={styles.metaDot} aria-hidden="true" />
          <span className={styles.cardReadTime}>{post.readingMinutes} min read</span>
        </div>
        <h3 className={styles.cardTitle}>
          <Link to={href} className={styles.cardTitleLink}>
            {post.title}
          </Link>
        </h3>
        <p className={styles.cardExcerpt}>{post.excerpt}</p>
      </div>
    </article>
  )
}

function ArrowRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}