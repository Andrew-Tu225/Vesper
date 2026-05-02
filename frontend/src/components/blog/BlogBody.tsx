import type { BlogBlock } from '../../content/blog/types'
import styles from './blog.module.css'

interface BlogBodyProps {
  blocks: BlogBlock[]
}

export function BlogBody({ blocks }: BlogBodyProps) {
  return (
    <div className={styles.body}>
      {blocks.map((block, i) => (
        <BlogBlockRenderer key={i} block={block} />
      ))}
    </div>
  )
}

interface BlockProps {
  block: BlogBlock
}

function BlogBlockRenderer({ block }: BlockProps) {
  switch (block.type) {
    case 'paragraph':
      return <p className={styles.bodyParagraph}>{block.text}</p>

    case 'heading':
      return block.level === 2
        ? <h2 className={styles.bodyH2}>{block.text}</h2>
        : <h3 className={styles.bodyH3}>{block.text}</h3>

    case 'pullquote':
      return (
        <blockquote className={styles.bodyPullquote}>
          <p className={styles.bodyPullquoteText}>{block.text}</p>
          {block.attribution && (
            <cite className={styles.bodyPullquoteCite}>{block.attribution}</cite>
          )}
        </blockquote>
      )

    case 'list':
      return block.style === 'numbered'
        ? (
          <ol className={styles.bodyList}>
            {block.items.map((item, i) => <li key={i} className={styles.bodyListItem}>{item}</li>)}
          </ol>
        )
        : (
          <ul className={styles.bodyList}>
            {block.items.map((item, i) => <li key={i} className={styles.bodyListItem}>{item}</li>)}
          </ul>
        )

    case 'callout':
      return (
        <aside className={`${styles.bodyCallout} ${styles[`bodyCallout${capitalize(block.tone)}`]}`}>
          <p className={styles.bodyCalloutText}>{block.text}</p>
        </aside>
      )

    case 'divider':
      return <hr className={styles.bodyDivider} />
  }
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}