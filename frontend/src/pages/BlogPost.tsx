import { useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { getPostBySlug, getRecentPosts } from '../content/blog'
import { BlogBody } from '../components/blog/BlogBody'
import { BlogMeta } from '../components/blog/BlogMeta'
import { BlogShareBar } from '../components/blog/BlogShareBar'
import { BlogCard } from '../components/blog/BlogCard'
import { PublicNav } from '../components/layout/PublicNav'
import { useSEO } from '../hooks/useSEO'
import styles from '../components/blog/blog.module.css'

const SITE_URL = 'https://tryvesper.vercel.app'

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const post = slug ? getPostBySlug(slug) : null

  useEffect(() => {
    if (!post) {
      navigate('/404', { replace: true })
    }
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [post, navigate])

  const seoTitle = post?.seo?.title ?? post?.title ?? ''
  const seoDescription = post?.seo?.description ?? post?.excerpt ?? ''
  const canonical = `/blog/${slug}`

  const jsonLd = post
    ? {
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: post.title,
        description: seoDescription,
        author: {
          '@type': 'Person',
          name: post.author.name,
          url: SITE_URL,
        },
        publisher: {
          '@type': 'Organization',
          name: 'Vesper',
          url: SITE_URL,
          logo: {
            '@type': 'ImageObject',
            url: `${SITE_URL}/logo.svg`,
          },
        },
        datePublished: post.publishedAt,
        dateModified: post.updatedAt ?? post.publishedAt,
        mainEntityOfPage: {
          '@type': 'WebPage',
          '@id': `${SITE_URL}/blog/${post.slug}`,
        },
        url: `${SITE_URL}/blog/${post.slug}`,
        articleSection: post.category,
        keywords: post.seo?.keywords?.join(', '),
      }
    : undefined

  useSEO({
    title: seoTitle,
    description: seoDescription,
    canonical,
    ogType: 'article',
    ogImage: post?.seo?.ogImage,
    article: post
      ? {
          publishedTime: post.publishedAt,
          modifiedTime: post.updatedAt,
          author: post.author.name,
          section: post.category,
          tags: post.seo?.keywords,
        }
      : undefined,
    jsonLd,
  })

  if (!post) return null

  const relatedPosts = getRecentPosts(post.slug, 2)

  return (
    <div className={styles.postPage}>
      <PublicNav />

      <article className={styles.postArticle}>
        <header className={styles.postHeader}>
          {post.eyebrow && (
            <span className={styles.postEyebrow}>{post.eyebrow}</span>
          )}
          <h1 className={styles.postTitle}>{post.title}</h1>
          {post.subtitle && (
            <p className={styles.postSubtitle}>{post.subtitle}</p>
          )}
          <BlogMeta post={post} layout="row" />
        </header>

        <div className={styles.postDivider} />

        <BlogBody blocks={post.body} />

        <div className={styles.postDivider} />

        <footer className={styles.postFooter}>
          <div className={styles.postAuthorCard}>
            <div className={styles.postAuthorInfo}>
              <span className={styles.postAuthorName}>{post.author.name}</span>
              <span className={styles.postAuthorRole}>{post.author.role}</span>
            </div>
          </div>
          <BlogShareBar title={post.title} slug={post.slug} />
        </footer>
      </article>

      {relatedPosts.length > 0 && (
        <section className={styles.relatedSection} aria-label="More posts">
          <h2 className={styles.relatedTitle}>More from the blog</h2>
          <div className={styles.relatedGrid}>
            {relatedPosts.map(p => (
              <BlogCard key={p.slug} post={p} />
            ))}
          </div>
        </section>
      )}

      <section className={styles.postCta}>
        <p className={styles.postCtaText}>Turn your team's Slack signals into LinkedIn posts — automatically.</p>
        <a href="/api/auth/google/login" className={styles.postCtaBtn}>
          Start self-hosting
        </a>
      </section>

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

function BackArrow() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M12 7H2M6 3L2 7l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}