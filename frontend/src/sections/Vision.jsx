import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';
import styles from './Vision.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] } },
};

export default function Vision() {
  const imgRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: imgRef,
    offset: ['start end', 'end start'],
  });
  const imgY = useTransform(scrollYProgress, [0, 1], ['0%', '-10%']);

  return (
    <section className={`section-pad ${styles.vision}`} id="vision">
      <div className="container">
        <div className={styles.grid}>
          <div className={styles.textCol}>
            <motion.p className={styles.sectionLabel} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              Our Vision
            </motion.p>
            <motion.h2 className={styles.title} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              From incident reports to{' '}
              <span className="text-gradient">actionable intelligence</span>
            </motion.h2>
            <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              Imagine a city where the moment an incident is reported, an intelligent system begins reasoning about its consequences. Not minutes later. Not after traffic has already accumulated. Immediately.
            </motion.p>
            <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              ASTRAM transforms a single traffic incident into a living operational picture. It analyzes what happened, where it happened, how severe it is likely to become, how long it may take to clear, which corridors are most vulnerable, and what actions traffic authorities should consider next.
            </motion.p>

            <motion.div className={styles.quoteCard} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              <p className={styles.quoteText}>
                Most navigation platforms answer a driver's question: <em>"Which route should I take?"</em>
                {' '}ASTRAM answers a city's question: <em>"What should we do next?"</em>
              </p>
            </motion.div>

            <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              That distinction changes everything. The objective is not to show congestion. The objective is to <strong>prevent</strong> it.
            </motion.p>
          </div>

          <motion.div className={styles.imageCol} ref={imgRef}>
            <motion.img
              src="/images/vision-control-room.png"
              alt="Modern traffic control center with real-time city monitoring"
              loading="lazy"
              style={{ y: imgY }}
            />
            <div className={styles.imageGlow} />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
