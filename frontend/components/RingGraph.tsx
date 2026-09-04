'use client';
import React, { useEffect, useRef } from 'react';
import type { GraphData } from '@/lib/api';

type N = { id: string; x: number; y: number; vx: number; vy: number; r: number };

export default function RingGraph({ data, verdict, type }: { data: GraphData; verdict: string; type?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = canvasRef.current; if (!cv) return;
    const x = cv.getContext('2d')!;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = window.devicePixelRatio || 1;
    let W = 0; const H = 400;

    const idIndex = new Map(data.nodes.map((n, i) => [n.id, i]));
    const nodes: N[] = [];
    const links: [number, number, string][] = [];

    function build() {
      W = cv!.clientWidth; cv!.width = W * dpr; cv!.height = H * dpr; x.setTransform(dpr, 0, 0, dpr, 0, 0);
      nodes.length = 0;
      const N = data.nodes.length;
      for (let i = 0; i < N; i++) {
        const a = (i / N) * Math.PI * 2;
        nodes.push({ id: data.nodes[i].id, x: W / 2 + Math.cos(a) * Math.min(150, W * 0.28) + (Math.random() - .5) * 40,
          y: H / 2 + Math.sin(a) * 130 + (Math.random() - .5) * 30, vx: 0, vy: 0, r: 8 + Math.random() * 7 });
      }
      links.length = 0;
      for (const e of data.edges) {
        const s = idIndex.get(e.source), t = idIndex.get(e.target);
        if (s !== undefined && t !== undefined) {
          const kind = e.kinds.includes('time') && e.kinds.length === 1 ? 'time' : e.kinds[0];
          links.push([s, t, kind]);
        }
      }
    }
    build();

    const isRing = verdict === 'fraud_ring';
    const col = isRing ? '#FF6B78' : '#3FE0A8';
    const glow = isRing ? 'rgba(229,72,77,.55)' : 'rgba(18,185,129,.5)';
    const EDGE: Record<string, string> = { device: '#E5484D', card: '#E08600', address: '#7A5CFF', ip: '#0D94FB', time: '#12B981' };
    const t0 = performance.now();
    let raf = 0;

    function loop() {
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i]; a.vx *= .86; a.vy *= .86;
        for (let j = 0; j < nodes.length; j++) { if (i === j) continue; const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy) || 1, f = Math.min(3, 1200 / (d * d)); a.vx += dx / d * f; a.vy += dy / d * f; }
        a.vx += (W / 2 - a.x) * .012; a.vy += (H / 2 - a.y) * .012;
      }
      for (const [i, j] of links) { const a = nodes[i], b = nodes[j], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1, f = (d - 90) * .012; a.vx += dx / d * f; a.vy += dy / d * f; b.vx -= dx / d * f; b.vy -= dy / d * f; }
      for (const n of nodes) { n.x += n.vx; n.y += n.vy; }
      x.clearRect(0, 0, W, H); const p = ((performance.now() - t0) / 1400) % 1;
      for (const [i, j, kind] of links) {
        const a = nodes[i], b = nodes[j], e = EDGE[kind] || '#0D94FB';
        x.strokeStyle = e + 'AA'; x.lineWidth = 1.6; x.beginPath(); x.moveTo(a.x, a.y); x.lineTo(b.x, b.y); x.stroke();
        if (!reduce) { const px = a.x + (b.x - a.x) * p, py = a.y + (b.y - a.y) * p; x.fillStyle = e; x.shadowColor = e; x.shadowBlur = 8; x.beginPath(); x.arc(px, py, 2.4, 0, 7); x.fill(); x.shadowBlur = 0; }
      }
      for (const n of nodes) {
        const g = x.createRadialGradient(n.x, n.y, n.r * .3, n.x, n.y, n.r + 16); g.addColorStop(0, glow); g.addColorStop(1, 'transparent');
        x.fillStyle = g; x.beginPath(); x.arc(n.x, n.y, n.r + 16, 0, 7); x.fill();
        x.fillStyle = col; x.shadowColor = glow; x.shadowBlur = 12; x.beginPath(); x.arc(n.x, n.y, n.r, 0, 7); x.fill(); x.shadowBlur = 0;
        x.strokeStyle = 'rgba(255,255,255,.9)'; x.lineWidth = 1.6; x.stroke();
      }
      raf = requestAnimationFrame(loop);
    }
    loop();
    const onResize = () => build();
    window.addEventListener('resize', onResize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); };
  }, [data, verdict, type]);

  return <canvas ref={canvasRef} style={{ width: '100%', height: 400, display: 'block' }} />;
}
