import { useState, useEffect, useCallback } from 'react';
import styles from './Navbar.module.css';

const NAV_LINKS = [
  { label: 'Problem', href: '#problem' },
  { label: 'Vision', href: '#vision' },
  { label: 'Intelligence', href: '#intelligence' },
  { label: 'Architecture', href: '#architecture' },
  { label: 'About', href: '#about' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [lastY, setLastY] = useState(0);

  const handleScroll = useCallback(() => {
    const y = window.scrollY;
    setScrolled(y > 50);
    setHidden(y > 300 && y > lastY);
    setLastY(y);
  }, [lastY]);

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const scrollTo = (e, href) => {
    e.preventDefault();
    setMenuOpen(false);
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <nav
      className={`${styles.nav} ${scrolled ? styles.scrolled : ''} ${hidden && !menuOpen ? styles.hidden : ''}`}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className={`container ${styles.navInner}`}>
        <a href="#" className={styles.logo} onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
          ASTRAM
        </a>

        <div className={styles.links}>
          {NAV_LINKS.map(({ label, href }) => (
            <a key={href} href={href} className={styles.link} onClick={(e) => scrollTo(e, href)}>
              {label}
            </a>
          ))}
          <a href="#contact" className={styles.cta} onClick={(e) => scrollTo(e, '#contact')}>
            Get in Touch
          </a>
        </div>

        <button
          className={`${styles.hamburger} ${menuOpen ? styles.open : ''}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-expanded={menuOpen}
          aria-label="Toggle menu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>

      <div className={`${styles.mobileMenu} ${menuOpen ? styles.open : ''}`}>
        {NAV_LINKS.map(({ label, href }) => (
          <a key={href} href={href} className={styles.mobileLink} onClick={(e) => scrollTo(e, href)}>
            {label}
          </a>
        ))}
        <a href="#contact" className={styles.cta} onClick={(e) => scrollTo(e, '#contact')}>
          Get in Touch
        </a>
      </div>
    </nav>
  );
}
