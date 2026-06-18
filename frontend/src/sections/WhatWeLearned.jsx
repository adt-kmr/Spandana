import { motion } from 'framer-motion';
import styles from './WhatWeLearned.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] } },
};

export default function WhatWeLearned() {
  return (
    <section className={`section-pad ${styles.learned}`}>
      <div className="container">
        <div className={styles.inner}>
          <motion.p className={styles.sectionLabel} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            What We Learned
          </motion.p>

          <motion.h2 className={styles.bigQuote} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            The most effective role for AI is not authority.{' '}
            <em className="text-gradient">It is augmentation.</em>
          </motion.h2>

          <div className={styles.divider} />

          <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            The biggest lesson was unexpected. The challenge was never building models. The challenge was deciding what role those models should play. Early in development, it was tempting to focus on automation — automated routing, automated deployment, automated operational decisions.
          </motion.p>

          <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            But cities are complex systems, and public infrastructure demands accountability. ASTRAM succeeds when it helps decision-makers see farther, understand faster, and act with greater confidence. Not when it attempts to replace them. That realization transformed the platform from a prediction engine into a decision-support system.
          </motion.p>

          <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            And ultimately, that became the product.
          </motion.p>
        </div>
      </div>
    </section>
  );
}
