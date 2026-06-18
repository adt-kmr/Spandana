import { motion } from 'framer-motion';
import styles from './About.module.css';

const TEAM = [
  { name: 'Team Member 1', role: 'ML & Backend', emoji: '🧠' },
  { name: 'Team Member 2', role: 'Data Engineering', emoji: '📊' },
  { name: 'Team Member 3', role: 'Frontend & Design', emoji: '🎨' },
  { name: 'Team Member 4', role: 'Infrastructure', emoji: '⚙️' },
];

export default function About() {
  return (
    <section className={`section-pad ${styles.about}`} id="about">
      <div className="container">
        <div className={styles.header}>
          <motion.p className={styles.sectionLabel} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
            The Team
          </motion.p>
          <motion.h2 className={styles.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.1 }}>
            Built for{' '}
            <span className="text-gradient--amber">Flipkart GRiD 7.0</span>
          </motion.h2>
          <motion.p className={styles.subtitle} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.2 }}>
            A team driven by the belief that cities can do better — that intelligence, not infrastructure, is the limiting factor in urban traffic management.
          </motion.p>
        </div>

        <div className={styles.teamGrid}>
          {TEAM.map((member, i) => (
            <motion.div
              key={i}
              className={styles.memberCard}
              initial={{ opacity: 0, y: 25 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className={styles.avatar}>{member.emoji}</div>
              <div className={styles.memberName}>{member.name}</div>
              <div className={styles.memberRole}>{member.role}</div>
            </motion.div>
          ))}
        </div>

        {/* Problem Statement card */}
        <motion.div
          className={styles.challengeCard}
          initial={{ opacity: 0, y: 25 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className={styles.challengeIcon}>⚙️</div>
          <div>
            <div className={styles.challengeTitle}>Event-Driven Congestion (Planned & Unplanned)</div>
            <div className={styles.challengeLabel}>Operational Challenge</div>
            <p className={styles.challengeText}>
              Political rallies, festivals, sports events, construction activities, and sudden gatherings create localized traffic breakdowns.
            </p>
            <div className={styles.challengeLabel}>Why It's Hard Today</div>
            <p className={styles.challengeText}>
              Event impact is not quantified in advance. Resource deployment is experience-driven. No post-event learning system.
            </p>
            <div className={styles.challengeLabel}>Problem Statement Direction</div>
            <p className={styles.challengeText}>
              How can historical and real-time data be used to forecast event-related traffic impact and recommend optimal manpower, barricading, and diversion plans?
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
