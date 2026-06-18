import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';
import styles from './LookingAhead.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
};

export default function LookingAhead() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  });
  const bgY = useTransform(scrollYProgress, [0, 1], ['0%', '20%']);

  return (
    <section className={`section-pad ${styles.lookingAhead}`} ref={ref}>
      <motion.div className={styles.bgWrap} style={{ y: bgY }}>
        <img src="/images/cityscape-ahead.png" alt="" loading="lazy" />
        <div className={styles.bgOverlay} />
      </motion.div>

      <div className={`container ${styles.content}`}>
        <motion.p className={styles.sectionLabel} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
          Looking Ahead
        </motion.p>

        <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
          Traffic management is often viewed as an infrastructure problem. In reality, it is an intelligence problem. Roads are finite. Budgets are finite. Personnel are finite. The ability to make better decisions is not.
        </motion.p>

        <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
          ASTRAM envisions a future where every traffic incident becomes a source of learning, every response becomes more informed, and every city becomes progressively more resilient. Not because congestion disappeared. But because cities learned how to stay ahead of it.
        </motion.p>

        <motion.h2
          className={styles.tagline}
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="text-gradient">Don't manage congestion.</span>
          <br />
          Anticipate it.
        </motion.h2>
      </div>
    </section>
  );
}
