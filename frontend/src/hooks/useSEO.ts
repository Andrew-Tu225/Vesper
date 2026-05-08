import { useEffect } from 'react'

const SITE_URL = 'https://tryvesper.vercel.app'
const SITE_NAME = 'Vesper'
const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`

interface ArticleMeta {
  publishedTime: string
  modifiedTime?: string | undefined
  author: string
  section?: string | undefined
  tags?: string[] | undefined
}

interface SEOConfig {
  title: string
  description: string
  canonical: string
  ogType?: 'website' | 'article' | undefined
  ogImage?: string | undefined
  article?: ArticleMeta | undefined
  jsonLd?: Record<string, unknown> | undefined
}

function upsertMeta(attribute: string, value: string, attrType: 'name' | 'property' = 'name') {
  let el = document.querySelector(`meta[${attrType}="${attribute}"]`) as HTMLMetaElement | null
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attrType, attribute)
    document.head.appendChild(el)
  }
  el.setAttribute('content', value)
}

function upsertLink(rel: string, href: string) {
  let el = document.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null
  if (!el) {
    el = document.createElement('link')
    el.rel = rel
    document.head.appendChild(el)
  }
  el.href = href
}

function upsertJsonLd(data: Record<string, unknown>) {
  let el = document.querySelector('script[type="application/ld+json"][data-dynamic-seo]') as HTMLScriptElement | null
  if (!el) {
    el = document.createElement('script')
    el.type = 'application/ld+json'
    el.setAttribute('data-dynamic-seo', 'true')
    document.head.appendChild(el)
  }
  el.textContent = JSON.stringify(data)
}

function removeJsonLd() {
  document.querySelector('script[type="application/ld+json"][data-dynamic-seo]')?.remove()
}

export function useSEO({ title, description, canonical, ogType = 'website', ogImage, article, jsonLd }: SEOConfig) {
  useEffect(() => {
    const pageTitle = `${title} | ${SITE_NAME}`
    const canonicalUrl = `${SITE_URL}${canonical}`
    const image = ogImage ?? DEFAULT_OG_IMAGE

    document.title = pageTitle

    upsertMeta('description', description)
    upsertMeta('robots', 'index, follow')

    upsertMeta('og:title', pageTitle, 'property')
    upsertMeta('og:description', description, 'property')
    upsertMeta('og:type', ogType, 'property')
    upsertMeta('og:url', canonicalUrl, 'property')
    upsertMeta('og:image', image, 'property')
    upsertMeta('og:image:width', '1200', 'property')
    upsertMeta('og:image:height', '630', 'property')
    upsertMeta('og:site_name', SITE_NAME, 'property')

    upsertMeta('twitter:card', 'summary_large_image')
    upsertMeta('twitter:title', pageTitle)
    upsertMeta('twitter:description', description)
    upsertMeta('twitter:image', image)

    if (ogType === 'article' && article) {
      upsertMeta('article:published_time', article.publishedTime, 'property')
      if (article.modifiedTime) {
        upsertMeta('article:modified_time', article.modifiedTime, 'property')
      }
      upsertMeta('article:author', article.author, 'property')
      if (article.section) {
        upsertMeta('article:section', article.section, 'property')
      }
      if (article.tags) {
        article.tags.forEach(tag => upsertMeta('article:tag', tag, 'property'))
      }
    }

    upsertLink('canonical', canonicalUrl)

    if (jsonLd) {
      upsertJsonLd(jsonLd)
    }

    return () => {
      document.title = 'Vesper | Turn Slack Updates Into LinkedIn Posts'
      removeJsonLd()
    }
  }, [title, description, canonical, ogType, ogImage, article, jsonLd])
}