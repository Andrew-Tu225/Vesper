import type { BlogPost } from '../../content/blog/types'
import styles from './blog.module.css'

interface BlogMetaProps {
  post: BlogPost
  layout?: 'row' | 'stack'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function BlogMeta({ post, layout = 'row' }: BlogMetaProps) {
  const { author, publishedAt, readingMinutes, category } = post

  return (
    <div className={`${styles.meta} ${layout === 'stack' ? styles.metaStack : ''}`}>
      <span className={styles.metaCategory}>{category.replace('-', ' ')}</span>
      <span className={styles.metaDot} aria-hidden="true" />
      <span className={styles.metaAuthor}>{author.name}</span>
      <span className={styles.metaDot} aria-hidden="true" />
      <time className={styles.metaDate} dateTime={publishedAt}>
        {formatDate(publishedAt)}
      </time>
      <span className={styles.metaDot} aria-hidden="true" />
      <span className={styles.metaRead}>{readingMinutes} min read</span>
    </div>
  )
}