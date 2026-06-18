import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';
import styles from './Hero.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.8, delay: i * 0.15, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function Hero() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  });
  const bgY = useTransform(scrollYProgress, [0, 1], ['0%', '30%']);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  return (
    <section className={styles.hero} ref={ref} id="hero">
      {/* Parallax background */}
      <motion.div className={styles.bgWrap} style={{ y: bgY }}>
        <img
          src="/images/hero-bg.png"
          alt=""
          className={styles.bgImage}
          fetchpriority="high"
          loading="eager"
        />
        <div className={styles.overlay} />
      </motion.div>

      <motion.div className={styles.content} style={{ opacity }}>
        <motion.p
          className={styles.tagline}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0}
        >
          Flipkart GRiD 7.0 — Traffic Intelligence
        </motion.p>

        <motion.h1
          className={styles.headline}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={1}
        >
          What if cities could{' '}
          <span className={styles.highlight}>respond</span> before congestion
          ever formed?
        </motion.h1>

        <motion.p
          className={styles.sub}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={2}
        >
          ASTRAM transforms traffic incidents into a living operational picture
          — analyzing severity, clearance time, corridor risk, and optimal
          response in real time.
        </motion.p>

        <motion.div
          className={styles.ctaRow}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={3}
        >
          <a href="#intelligence" className={styles.ctaPrimary} onClick={(e) => { e.preventDefault(); document.querySelector('#intelligence')?.scrollIntoView({ behavior: 'smooth' }); }}>
            Explore the Platform ↓
          </a>
          <a href="#problem" className={styles.ctaSecondary} onClick={(e) => { e.preventDefault(); document.querySelector('#problem')?.scrollIntoView({ behavior: 'smooth' }); }}>
            See the Problem
          </a>
        </motion.div>
      </motion.div>

      <div className={styles.scrollIndicator}>
        <div className={styles.scrollDot} />
        <span>Scroll</span>
      </div>
    </section>
  );
}
