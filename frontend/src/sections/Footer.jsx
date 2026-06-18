import { motion } from 'framer-motion';
import styles from './Footer.module.css';

const scrollTo = (e, href) => {
  e.preventDefault();
  const el = document.querySelector(href);
  if (el) el.scrollIntoView({ behavior: 'smooth' });
};

export default function Footer() {
  return (
    <footer className={styles.footer} id="contact">
      <div className="container">
        <div className={styles.footerGrid}>
          {/* Brand */}
          <div className={styles.brand}>
            <div className={styles.brandLogo}>ASTRAM</div>
            <p className={styles.brandDesc}>
              A multimodal traffic intelligence platform that transforms incident reports into actionable intelligence. Built for Bengaluru. Designed for every city.
            </p>
          </div>

          {/* Navigation */}
          <nav className={styles.navCol} aria-label="Footer navigation">
            <div className={styles.navColTitle}>Navigate</div>
            <a href="#problem" className={styles.navLink} onClick={(e) => scrollTo(e, '#problem')}>Problem</a>
            <a href="#vision" className={styles.navLink} onClick={(e) => scrollTo(e, '#vision')}>Vision</a>
            <a href="#intelligence" className={styles.navLink} onClick={(e) => scrollTo(e, '#intelligence')}>Intelligence Engine</a>
            <a href="#architecture" className={styles.navLink} onClick={(e) => scrollTo(e, '#architecture')}>Architecture</a>
            <a href="#about" className={styles.navLink} onClick={(e) => scrollTo(e, '#about')}>About</a>
          </nav>

          {/* Contact */}
          <div className={styles.contactCol}>
            <div className={styles.contactTitle}>Get in Touch</div>
            <a href="mailto:team@astram.dev" className={styles.contactLink}>
              team@astram.dev
            </a>
            <a href="https://github.com" className={styles.contactLink} target="_blank" rel="noopener noreferrer">
              GitHub Repository →
            </a>
          </div>
        </div>

        {/* Bottom bar */}
        <div className={styles.bottom}>
          <p className={styles.copyright}>
            © {new Date().getFullYear()} ASTRAM. All rights reserved.
          </p>
          <div className={styles.badge}>
            🏆 Flipkart GRiD 7.0
          </div>
          <p className={styles.love}>
            Built with ❤️ in Bengaluru
          </p>
        </div>
      </div>
    </footer>
  );
}
