import { motion, useInView } from 'framer-motion';
import { useRef, useEffect, useState } from 'react';
import styles from './Problem.module.css';

const STATS = [
  { number: '₹1.47L Cr', label: 'Annual economic cost of traffic congestion in India', source: 'BCG Report, 2024' },
  { number: '243', label: 'Hours lost per year by Bengaluru commuters in traffic', source: 'TomTom Traffic Index' },
  { number: '11,000+', label: 'Road accident fatalities annually in Karnataka alone', source: 'NCRB Data, 2023' },
  { number: '7 / 10', label: 'Of India\'s most congested stretches are in Bengaluru', source: 'Ola Mobility Institute' },
];

function AnimatedNumber({ value, inView }) {
  const [display, setDisplay] = useState(value);
  const numericMatch = value.match(/[\d,.]+/);

  useEffect(() => {
    if (!inView || !numericMatch) { setDisplay(value); return; }
    const target = parseFloat(numericMatch[0].replace(/,/g, ''));
    if (isNaN(target)) { setDisplay(value); return; }
    const prefix = value.slice(0, numericMatch.index);
    const suffix = value.slice(numericMatch.index + numericMatch[0].length);
    let start = 0;
    const duration = 1200;
    const startTime = performance.now();

    const step = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      start = eased * target;
      const formatted = target >= 100
        ? Math.round(start).toLocaleString('en-IN')
        : start.toFixed(target % 1 === 0 ? 0 : 2);
      setDisplay(`${prefix}${formatted}${suffix}`);
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [inView, value, numericMatch]);

  return <>{display}</>;
}

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] } },
};

export default function Problem() {
  const statsRef = useRef(null);
  const statsInView = useInView(statsRef, { once: true, margin: '-100px' });

  return (
    <section className={`section-pad ${styles.problem}`} id="problem">
      <div className="container">
        {/* Stats grid */}
        <div className={styles.statsGrid} ref={statsRef}>
          {STATS.map((stat, i) => (
            <motion.div
              key={i}
              className={styles.statCard}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.6, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className={styles.statNumber}>
                <AnimatedNumber value={stat.number} inView={statsInView} />
              </div>
              <div className={styles.statLabel}>{stat.label}</div>
              <div className={styles.statSource}>{stat.source}</div>
            </motion.div>
          ))}
        </div>

        {/* Narrative */}
        <div className={styles.narrative}>
          <motion.p className={styles.sectionLabel} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            The Problem
          </motion.p>
          <motion.h2 className={styles.sectionTitle} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            The incident is rarely the problem.{' '}
            <span className="text-gradient">The delay is.</span>
          </motion.h2>

          <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            Every traffic jam has a visible beginning. A stalled truck on a major corridor. A minor collision at a busy intersection. A waterlogged underpass after an unexpected downpour. But congestion does not begin where we think it does.
          </motion.p>
          <motion.p className={styles.paragraph} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            By the time drivers see brake lights stretching toward the horizon, the real damage has already started. Ambulances lose precious minutes. Office workers lose productive hours. Delivery fleets miss schedules. Emergency responders are forced into reactive decisions rather than strategic ones.
          </motion.p>

          <motion.blockquote className={styles.pullQuote} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            Cities do not suffer because incidents occur. Cities suffer because they discover the impact too late.
          </motion.blockquote>
        </div>

        <motion.div
          className={styles.imageWrap}
          initial={{ opacity: 0, scale: 0.97 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <img src="/images/problem-traffic.png" alt="Bengaluru traffic congestion during peak hours" loading="lazy" />
          <div className={styles.imageCaption}>Peak-hour congestion on a Bengaluru arterial road — a daily reality for 13 million commuters.</div>
        </motion.div>
      </div>
    </section>
  );
}
