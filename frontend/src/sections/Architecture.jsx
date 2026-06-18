import { motion, useInView } from 'framer-motion';
import { useRef, useState, useEffect } from 'react';
import styles from './Architecture.module.css';

const PIPELINE = [
  { icon: '📥', label: 'Ingest' },
  { icon: '✅', label: 'Validate' },
  { icon: '🗄️', label: 'Store' },
  { icon: '🧠', label: 'Infer' },
  { icon: '🔒', label: 'Verify' },
  { icon: '🚀', label: 'Serve' },
];

const TECH = [
  { icon: '🐍', name: 'Python' },
  { icon: '⚡', name: 'FastAPI' },
  { icon: '🌿', name: 'LightGBM' },
  { icon: '📊', name: 'Lifelines' },
  { icon: '🐘', name: 'PostgreSQL' },
  { icon: '🐳', name: 'Docker' },
  { icon: '⚛️', name: 'React' },
  { icon: '🎞️', name: 'Framer Motion' },
  { icon: '📦', name: 'scikit-learn' },
  { icon: '🔧', name: 'OR-Tools' },
];

export default function Architecture() {
  const pipeRef = useRef(null);
  const inView = useInView(pipeRef, { once: true, margin: '-100px' });
  const [activeIdx, setActiveIdx] = useState(-1);

  useEffect(() => {
    if (!inView) return;
    const timers = PIPELINE.map((_, i) =>
      setTimeout(() => setActiveIdx(i), 300 + i * 250)
    );
    return () => timers.forEach(clearTimeout);
  }, [inView]);

  return (
    <section className={`section-pad ${styles.architecture}`} id="architecture">
      <div className="container">
        <div className={styles.header}>
          <motion.p className={styles.sectionLabel} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
            Architecture
          </motion.p>
          <motion.h2 className={styles.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.1 }}>
            Event-driven.{' '}
            <span className="text-gradient">Real-time.</span>
          </motion.h2>
        </div>

        {/* Pipeline diagram */}
        <div className={styles.pipeline} ref={pipeRef}>
          {PIPELINE.map((node, i) => (
            <motion.div key={node.label} style={{ display: 'contents' }}>
              <motion.div
                className={`${styles.pipeNode} ${i <= activeIdx ? styles.active : ''}`}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <div className={styles.nodeCircle}>{node.icon}</div>
                <span className={styles.nodeLabel}>{node.label}</span>
              </motion.div>
              {i < PIPELINE.length - 1 && <div className={styles.pipeArrow} />}
            </motion.div>
          ))}
        </div>

        {/* Tech stack */}
        <motion.p className={styles.techTitle} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
          Built With
        </motion.p>
        <div className={styles.badges}>
          {TECH.map((t, i) => (
            <motion.div
              key={t.name}
              className={styles.badge}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
            >
              <span className={styles.badgeIcon}>{t.icon}</span>
              {t.name}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
