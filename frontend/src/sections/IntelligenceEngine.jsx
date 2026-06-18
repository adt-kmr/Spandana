import { motion } from 'framer-motion';
import styles from './IntelligenceEngine.module.css';

const SYSTEMS = [
  {
    num: '01',
    icon: '🛡️',
    title: 'Severity Intelligence',
    desc: 'Evaluates incident attributes, roadway conditions, and descriptive reports to estimate operational severity — not a raw score, but a calibrated band with confidence that helps authorities prioritize where intervention creates the greatest impact.',
    key: 'Calibrated classifier · LightGBM · Platt scaling',
    color: 'var(--color-accent)',
    dim: 'var(--color-accent-dim)',
  },
  {
    num: '02',
    icon: '⏱️',
    title: 'Clearance-Time Forecasting',
    desc: 'Estimates probable clearance windows using censored survival analysis rather than point predictions. Instead of a single rigid ETA, it provides confidence ranges — because intelligent systems should express what they don\'t know.',
    key: 'Weibull AFT · Right-censored · Median + P10–P90',
    color: 'var(--color-teal)',
    dim: 'var(--color-teal-dim)',
  },
  {
    num: '03',
    icon: '🛣️',
    title: 'Corridor Risk Prediction',
    desc: 'Continuously evaluates how current incidents influence traffic across the network over the coming 3 hours. Identifies vulnerable corridors before congestion reaches critical levels. Anticipation, not observation.',
    key: '3-hour nowcast · LightGBM · Lagged features',
    color: 'var(--color-red)',
    dim: 'var(--color-red-dim)',
  },
];

const BOTTOM = [
  {
    num: '04',
    icon: '📍',
    title: 'Hotspot Discovery',
    desc: 'Identifies recurring spatial patterns automatically — junctions with repeated breakdowns, roads that flood during rainfall, bottlenecks during events — moving beyond incident management toward long-term infrastructure improvement.',
    key: 'DBSCAN clustering · Haversine distance · BallTree',
    color: 'var(--color-orange)',
    dim: 'var(--color-orange-dim)',
  },
  {
    num: '05',
    icon: '🚀',
    title: 'Response Optimization',
    desc: 'Transforms resource allocation into structured recommendations — which team, which corridor, which response creates the greatest operational benefit. Not commands. Recommendations. Human expertise remains central.',
    key: 'OR-Tools assignment · FIFO baseline · Haversine ETA',
    color: 'var(--color-blue)',
    dim: 'var(--color-blue-dim)',
  },
];

function Card({ system, index }) {
  return (
    <motion.div
      className={styles.card}
      initial={{ opacity: 0, y: 30, scale: 0.96 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.6, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
      style={{ '--card-color': system.color }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = system.color + '40'; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = ''; }}
    >
      <div className={styles.cardGlow} style={{ background: `linear-gradient(90deg, ${system.color}, transparent)` }} />
      <div className={styles.cardNumber}>{system.num}</div>
      <div className={styles.cardIcon} style={{ background: system.dim }}>
        {system.icon}
      </div>
      <h3 className={styles.cardTitle}>{system.title}</h3>
      <p className={styles.cardDesc}>{system.desc}</p>
      <p className={styles.cardKey}>{system.key}</p>
    </motion.div>
  );
}

export default function IntelligenceEngine() {
  return (
    <section className={`section-pad ${styles.intelligence}`} id="intelligence">
      <div className="container">
        <div className={styles.header}>
          <motion.p className={styles.sectionLabel} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
            The Intelligence Engine
          </motion.p>
          <motion.h2 className={styles.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.1 }}>
            Five interconnected{' '}
            <span className="text-gradient">decision systems</span>
          </motion.h2>
          <motion.p className={styles.subtitle} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.2 }}>
            At its core, ASTRAM is a multimodal traffic intelligence platform. When a new incident arrives, it immediately evaluates severity, clearance time, corridor risk, hotspot patterns, and optimal response.
          </motion.p>
        </div>

        {/* Top 3 cards */}
        <div className={styles.cardsGrid}>
          {SYSTEMS.map((sys, i) => (
            <Card key={sys.num} system={sys} index={i} />
          ))}
        </div>

        {/* Bottom 2 cards — centered */}
        <div className={styles.bottomRow}>
          {BOTTOM.map((sys, i) => (
            <Card key={sys.num} system={sys} index={i + 3} />
          ))}
        </div>
      </div>
    </section>
  );
}
