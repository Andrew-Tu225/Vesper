import { useState } from 'react'
import styles from './blog.module.css'

interface BlogShareBarProps {
  title: string
  slug: string
}

const SITE_URL = 'https://tryvesper.vercel.app'

export function BlogShareBar({ title, slug }: BlogShareBarProps) {
  const [copied, setCopied] = useState(false)
  const postUrl = `${SITE_URL}/blog/${slug}`

  function handleCopy() {
    navigator.clipboard.writeText(postUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const linkedinShareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(postUrl)}`

  return (
    <div className={styles.shareBar}>
      <span className={styles.shareLabel}>Share</span>
      <a
        href={linkedinShareUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={styles.shareBtn}
        aria-label="Share on LinkedIn"
      >
        <LinkedInIcon />
        LinkedIn
      </a>
      <button
        className={styles.shareBtn}
        onClick={handleCopy}
        aria-label="Copy link to clipboard"
      >
        <LinkIcon />
        {copied ? 'Copied!' : 'Copy link'}
      </button>
    </div>
  )
}

function LinkedInIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  )
}

function LinkIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
    </svg>
  )
}