'use client';
import React, { useEffect, useRef, useState } from 'react';
import { inr } from '@/lib/api';
export function CountUp({ value, money }: { value: number; money?: boolean }) {
  const [n, setN] = useState(0); const raf = useRef(0);
  useEffect(() => {
    const start = performance.now(), dur = 1300;
    const tick = (now: number) => { const p = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - p, 3); setN(value * e); if (p < 1) raf.current = requestAnimationFrame(tick); };
    raf.current = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf.current);
  }, [value]);
  return <>{money ? inr(n) : Math.round(n).toLocaleString()}</>;
}
export function Clock() {
  const [t, setT] = useState('');
  useEffect(() => { const f = () => setT(new Date().toLocaleTimeString('en-IN', { hour12: false }) + ' IST'); f(); const id = setInterval(f, 1000); return () => clearInterval(id); }, []);
  return <span className="mono">{t}</span>;
}
