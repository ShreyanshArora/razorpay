'use client';
import React from 'react';

export const VERDICT_STYLE: Record<string, { fg: string; glow: string; label: string }> = {
  fraud_ring: { fg: 'var(--critical)', glow: 'var(--critical-glow)', label: 'Fraud ring' },
  office:     { fg: 'var(--clear)', glow: 'var(--clear-glow)', label: 'Office' },
  family:     { fg: 'var(--clear)', glow: 'var(--clear-glow)', label: 'Family' },
  reseller:   { fg: 'var(--clear)', glow: 'var(--clear-glow)', label: 'Reseller' },
  inconclusive:{ fg: 'var(--warn)', glow: 'transparent', label: 'Inconclusive' },
};

export function VerdictBadge({ verdict }: { verdict: string }) {
  const s = VERDICT_STYLE[verdict] ?? VERDICT_STYLE.inconclusive;
  return (
    <span style={{
      color: s.fg, fontWeight: 600, fontSize: 11.5,
      padding: '3px 10px', borderRadius: 999, letterSpacing: '.02em',
      display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
      background: 'color-mix(in srgb, ' + s.fg + ' 12%, transparent)',
      border: '1px solid color-mix(in srgb, ' + s.fg + ' 30%, transparent)',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: s.fg,
        boxShadow: '0 0 8px ' + s.glow }} />
      {s.label}
    </span>
  );
}

export function Kpi({ label, value, sub, tone, delay = 0 }: {
  label: string; value: React.ReactNode; sub?: string; tone?: 'critical' | 'clear' | 'brand'; delay?: number;
}) {
  const toneColor = tone === 'critical' ? 'var(--critical)' : tone === 'clear' ? 'var(--clear)'
    : tone === 'brand' ? 'var(--brand-2)' : 'var(--ink)';
  const glow = tone === 'critical' ? 'var(--critical-glow)' : tone === 'clear' ? 'var(--clear-glow)'
    : tone === 'brand' ? 'var(--brand-glow)' : 'transparent';
  return (
    <div className="glass rise" style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column',
      gap: 7, minWidth: 0, position: 'relative', overflow: 'hidden', animationDelay: delay + 'ms' }}>
      <div style={{ position: 'absolute', top: -30, right: -30, width: 90, height: 90, borderRadius: 999,
        background: glow, filter: 'blur(36px)', opacity: .5, pointerEvents: 'none' }} />
      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-3)',
        textTransform: 'uppercase', letterSpacing: '.08em' }}>{label}</span>
      <span className="tnum" style={{ fontSize: 29, fontWeight: 800, color: toneColor,
        letterSpacing: '-.02em', lineHeight: 1.05,
        textShadow: glow !== 'transparent' ? '0 0 24px ' + glow : 'none' }}>{value}</span>
      {sub && <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>{sub}</span>}
    </div>
  );
}

export function Card({ children, style, pad = 20, className = '' }:
  { children: React.ReactNode; style?: React.CSSProperties; pad?: number; className?: string }) {
  return <div className={'glass ' + className} style={{ padding: pad, ...style }}>{children}</div>;
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-3)',
    textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 12 }}>{children}</div>;
}
