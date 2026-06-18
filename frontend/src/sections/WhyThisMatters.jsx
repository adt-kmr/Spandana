import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';
import styles from './WhyThisMatters.module.css';

const STEPS = [
  {
    num: '01',
    title: 'An incident is reported',
    desc: 'A stalled vehicle, minor collision, or waterlogging occurs. The first ripple is felt, but context is missing.',
  },
  {
    num: '02',
    title: 'Operators examine dashboards',
    desc: 'Multiple disjointed feeds (GPS, cameras, reports) compete for attention. Correlating them takes precious time.',
  },
  {
    num: '03',
    title: 'Field teams exchange calls',
    desc: 'Traffic police and response units coordinate manually. Information degrades as it passes between teams.',
  },
  {
    num: '04',
    title: 'Decisions are made manually',
    desc: 'Manpower, barricading, and diversions are deployed based on experience rather than predictive simulation.',
  },
  {
    num: '05',
    title: 'Traffic spreads through the network',
    desc: 'Meanwhile, delays ripple outwards. A minor 10-minute bottleneck morphs into a gridlocked corridor.',
  },
];

export default function WhyThisMatters() {
  const containerRef = useRef(null);
  
  // Track scroll position of the section
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start center', 'end center'],
  });

  // Scale height of progress line from 0 to 1
  const scaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <section className={`section-pad ${styles.whyThisMatters}`} id="matters" ref={containerRef}>
      <div className="container">
        <div className={styles.header}>
          <motion.span 
            className={styles.sectionLabel}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            The Gap
          </motion.span>
          <motion.h2 
            className={styles.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            Why This <span className="text-gradient">Matters</span>
          </motion.h2>
          <motion.p 
            className={styles.subtitle}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            The lag between detecting an incident and deploying a response is where congestion goes from localized delay to systemic gridlock.
          </motion.p>
        </div>

        <div className={styles.timelineContainer}>
          {/* Static Background Line */}
          <div className={styles.timelineLine} />
          
          {/* Animated Progress Line */}
          <motion.div 
            className={styles.timelineProgressLine} 
            style={{ scaleY }} 
          />

          {STEPS.map((step, index) => {
            const isEven = index % 2 === 0;
            return (
              <div key={index} className={styles.timelineRow}>
                {/* Visual Dot on Timeline */}
                <motion.div 
                  className={styles.timelineDot}
                  initial={{ scale: 0, opacity: 0 }}
                  whileInView={{ scale: 1, opacity: 1 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.4, delay: 0.15 }}
                />

                {/* Card Container */}
                <motion.div 
                  className={styles.cardWrapper}
                  initial={{ 
                    opacity: 0, 
                    x: isEven ? 50 : -50 
                  }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: '-100px' }}
                  transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className={styles.card}>
                    <div className={styles.cardNum}>{step.num}</div>
                    <h3 className={styles.cardTitle}>{step.title}</h3>
                    <p className={styles.cardDesc}>{step.desc}</p>
                  </div>
                </motion.div>
              </div>
            );
          })}
        </div>

        {/* Concluding callout */}
        <div className={styles.calloutContainer}>
          <motion.div 
            className={styles.calloutCard}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <div className={styles.calloutText}>
              "The challenge is not a lack of information. The challenge is converting information into action quickly enough to matter."
            </div>
            <div className={styles.calloutSubtext}>
              ASTRAM fills this gap by turning raw telematics and event schedules into real-time decision recommendations.
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
