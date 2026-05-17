import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../lib/constants'
import styles from './publicNav.module.css'

export function PublicNav() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 80)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav className={`${styles.nav} ${scrolled ? styles.navScrolled : ''}`}>
      <div className={styles.navInner}>
        <div className={styles.navLogo}>
          <a href="/">
            <img src="/logo.svg" alt="Vesper" height="56" />
          </a>
        </div>
        <div className={styles.navLinks}>
          <a href="/#how-it-works" className={styles.navLink}>How it works</a>
          <Link to={ROUTES.BLOG_INDEX} className={styles.navLink}>Blog</Link>
          <a href="/#open-source" className={styles.navLink}>Open source</a>
        </div>
        <Link to={ROUTES.LOGIN} className={styles.navLogin}>Login</Link>
        <button
          className={styles.navHamburger}
          onClick={() => setMenuOpen(o => !o)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
        >
          <span className={`${styles.hamburgerLine} ${menuOpen ? styles.hamburgerLineTopOpen : ''}`} />
          <span className={`${styles.hamburgerLine} ${menuOpen ? styles.hamburgerLineMidOpen : ''}`} />
          <span className={`${styles.hamburgerLine} ${menuOpen ? styles.hamburgerLineBotOpen : ''}`} />
        </button>
      </div>
      {menuOpen && (
        <div className={styles.mobileMenu}>
          <a href="/#how-it-works" className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>How it works</a>
          <Link to={ROUTES.BLOG_INDEX} className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>Blog</Link>
          <a href="/#open-source" className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>Open source</a>
          <Link to={ROUTES.LOGIN} className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>Login</Link>
        </div>
      )}
    </nav>
  )
}
