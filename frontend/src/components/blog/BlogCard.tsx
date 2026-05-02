import { Link } from 'react-router-dom'
import type { BlogPost } from '../../content/blog/types'
import { BlogMeta } from './BlogMeta'
import { blogPostHref } from '../../lib/constants'
import styles from './blog.module.css'

interface BlogCardProps {
  post: BlogPost
  variant?: 'featured' | 'default'
}

export function BlogCard({ post, variant = 'default' }: BlogCardProps) {
  const href = blogPostHref(post.slug)

  if (variant === 'featured') {
    return (
      <article className={styles.featuredCard}>
        {post.eyebrow && (
          <span className={styles.cardEyebrow}>{post.eyebrow}</span>
        )}
        <h2 className={styles.featuredCardTitle}>
          <Link to={href} className={styles.cardTitleLink}>
            {post.title}
          </Link>
        </h2>
        {post.subtitle && (
          <p className={styles.featuredCardSubtitle}>{post.subtitle}</p>
        )}
        <BlogMeta post={post} />
        <Link to={href} className={styles.cardReadMore} aria-label={`Read ${post.title}`}>
          Read post <ArrowRight />
        </Link>
      </article>
    )
  }

  return (
    <article className={styles.card}>
      {post.eyebrow && (
        <span className={styles.cardEyebrow}>{post.eyebrow}</span>
      )}
      <h3 className={styles.cardTitle}>
        <Link to={href} className={styles.cardTitleLink}>
          {post.title}
        </Link>
      </h3>
      <p className={styles.cardExcerpt}>{post.excerpt}</p>
      <BlogMeta post={post} />
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