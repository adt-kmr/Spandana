import { useEffect, useRef } from 'react';

type Props = { className?: string };

export default function RoadNetworkBackground({ className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const activeCanvas = canvas as HTMLCanvasElement;
    const activeCtx = ctx as CanvasRenderingContext2D;

    const prefersReduced =
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

    // ---- Theme (dark futuristic map, lightly brand-tinted) ----
    const BG = '#0a0e1a';
    const ROAD = 'rgba(120, 140, 180, 0.14)';
    const ROAD_BRIGHT = 'rgba(150, 175, 220, 0.30)';
    const VEHICLE_COLORS = ['#4d90fe', '#2ecc71', '#ffdc00', '#e2e8f0'];

    const GRID = 92;     // spacing between roads (CSS px)
    const JITTER = 18;   // slight irregularity so it isn't a perfect grid
    const SPEED = 14;    // base px/sec — intentionally slow
    const VEHICLES_PER_ROAD = 0.6;

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    type Line = { pos: number; bright: boolean };
    let cols: Line[] = [];
    let rows: Line[] = [];

    type Vehicle = {
      axis: 'h' | 'v';
      track: number;
      t: number;
      speed: number;
      dir: 1 | -1;
      color: string;
      size: number;
    };
    let vehicles: Vehicle[] = [];

    type Node = { x: number; y: number; phase: number };
    let nodes: Node[] = [];

    const rand = (a: number, b: number) => a + Math.random() * (b - a);
    const pick = <T,>(arr: T[]): T => arr[(Math.random() * arr.length) | 0] as T;

    function build() {
      cols = [];
      rows = [];
      for (let x = GRID / 2; x < width; x += GRID) {
        cols.push({ pos: x + rand(-JITTER, JITTER), bright: Math.random() < 0.25 });
      }
      for (let y = GRID / 2; y < height; y += GRID) {
        rows.push({ pos: y + rand(-JITTER, JITTER), bright: Math.random() < 0.25 });
      }

      nodes = [];
      for (const c of cols) {
        for (const r of rows) {
          if (Math.random() < 0.08) nodes.push({ x: c.pos, y: r.pos, phase: rand(0, Math.PI * 2) });
        }
      }

      vehicles = [];
      const total = Math.round((cols.length + rows.length) * VEHICLES_PER_ROAD);
      for (let i = 0; i < total; i++) {
        const horiz = Math.random() < 0.5;
        if (horiz && rows.length) {
          const r = pick(rows);
          vehicles.push({
            axis: 'h', track: r.pos, t: rand(0, width || 1),
            speed: SPEED * rand(0.6, 1.5), dir: Math.random() < 0.5 ? 1 : -1,
            color: pick(VEHICLE_COLORS), size: rand(1.6, 2.8),
          });
        } else if (cols.length) {
          const c = pick(cols);
          vehicles.push({
            axis: 'v', track: c.pos, t: rand(0, height || 1),
            speed: SPEED * rand(0.6, 1.5), dir: Math.random() < 0.5 ? 1 : -1,
            color: pick(VEHICLE_COLORS), size: rand(1.6, 2.8),
          });
        }
      }
    }

    function resize() {
      const parent = activeCanvas.parentElement;
      const rect = parent
        ? parent.getBoundingClientRect()
        : { width: window.innerWidth, height: window.innerHeight };
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      activeCanvas.width = Math.floor(width * dpr);
      activeCanvas.height = Math.floor(height * dpr);
      activeCanvas.style.width = `${width}px`;
      activeCanvas.style.height = `${height}px`;
      activeCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      build();
      if (prefersReduced) drawStatic();
    }

    function drawGrid() {
      activeCtx.lineWidth = 1;
      for (const c of cols) {
        activeCtx.strokeStyle = c.bright ? ROAD_BRIGHT : ROAD;
        activeCtx.beginPath();
        activeCtx.moveTo(c.pos, 0);
        activeCtx.lineTo(c.pos, height);
        activeCtx.stroke();
      }
      for (const r of rows) {
        activeCtx.strokeStyle = r.bright ? ROAD_BRIGHT : ROAD;
        activeCtx.beginPath();
        activeCtx.moveTo(0, r.pos);
        activeCtx.lineTo(width, r.pos);
        activeCtx.stroke();
      }
    }

    function drawNodes(time: number) {
      for (const n of nodes) {
        const pulse = 0.5 + 0.5 * Math.sin(time * 0.0012 + n.phase);
        const radius = 2 + pulse * 3;
        activeCtx.beginPath();
        activeCtx.fillStyle = `rgba(255, 220, 0, ${0.10 + pulse * 0.22})`;
        activeCtx.arc(n.x, n.y, radius, 0, Math.PI * 2);
        activeCtx.fill();
      }
    }

    function drawVehicle(v: Vehicle) {
      const x = v.axis === 'h' ? v.t : v.track;
      const y = v.axis === 'h' ? v.track : v.t;
      const glow = activeCtx.createRadialGradient(x, y, 0, x, y, v.size * 4);
      glow.addColorStop(0, v.color);
      glow.addColorStop(1, 'rgba(0,0,0,0)');
      activeCtx.fillStyle = glow;
      activeCtx.beginPath();
      activeCtx.arc(x, y, v.size * 4, 0, Math.PI * 2);
      activeCtx.fill();
      activeCtx.fillStyle = v.color;
      activeCtx.beginPath();
      activeCtx.arc(x, y, v.size, 0, Math.PI * 2);
      activeCtx.fill();
    }

    function drawStatic() {
      activeCtx.fillStyle = BG;
      activeCtx.fillRect(0, 0, width, height);
      drawGrid();
      drawNodes(0);
      for (const v of vehicles) drawVehicle(v);
    }

    let raf = 0;
    let last = performance.now();

    function frame(now: number) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      activeCtx.fillStyle = BG;
      activeCtx.fillRect(0, 0, width, height);
      drawGrid();
      drawNodes(now);

      for (const v of vehicles) {
        v.t += v.dir * v.speed * dt;
        const len = v.axis === 'h' ? width : height;
        if (v.t > len + 20) v.t = -20;
        if (v.t < -20) v.t = len + 20;
        drawVehicle(v);
      }
      raf = requestAnimationFrame(frame);
    }

    const ro = new ResizeObserver(() => resize());
    if (activeCanvas.parentElement) ro.observe(activeCanvas.parentElement);
    resize();

    if (prefersReduced) {
      return () => ro.disconnect();
    }

    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(raf);
      } else {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={className}
      style={{ display: 'block', pointerEvents: 'none' }}
    />
  );
}
