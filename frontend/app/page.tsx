'use client';
import React, { useEffect, useState } from 'react';
import { api, inr, Overview, CaseRow, EvalResults } from '@/lib/api';
import { CountUp, Clock } from '@/components/CountUp';
import CasePanel from '@/components/CasePanel';

const CLS: Record<string, string> = { fraud_ring: 'crit', office: 'clear', family: 'clear', reseller: 'clear', inconclusive: 'warn' };
const VLABEL: Record<string, string> = { fraud_ring: 'Fraud ring', office: 'Office', family: 'Family', reseller: 'Reseller', inconclusive: 'Inconclusive' };
function badge(verdict: string) {
  const c = CLS[verdict] || 'warn';
  const color = c === 'crit' ? 'var(--crit)' : c === 'warn' ? 'var(--warn)' : 'var(--clear)';
  const wash = c === 'crit' ? 'var(--crit-wash)' : c === 'warn' ? 'var(--warn-wash)' : 'var(--clear-wash)';
  return (
    <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 999, color, background: wash,
      border: `1px solid color-mix(in srgb, ${color} 28%, transparent)`, display: 'inline-flex', alignItems: 'center', gap: 5, whiteSpace: 'nowrap' }}>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: color, boxShadow: `0 0 7px ${color}` }} />{VLABEL[verdict] || verdict}
    </span>
  );
}

function Logo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ width: 32, height: 32, borderRadius: 9, background: 'linear-gradient(135deg,var(--brand),var(--brand-2))',
        display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 18px var(--brand-glow)' }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="5" cy="6" r="2.4" fill="#fff" /><circle cx="19" cy="7" r="2.4" fill="#fff" /><circle cx="12" cy="18" r="2.4" fill="#fff" /><path d="M5 6L19 7M19 7L12 18M12 18L5 6" stroke="#fff" strokeWidth="1.4" opacity=".75" /></svg>
      </div>
      <div><div style={{ fontWeight: 800, fontSize: 16, color: '#fff', letterSpacing: '.02em' }}>NEXUS</div>
        <div style={{ fontSize: 9, color: '#6E86A8', letterSpacing: '.14em', marginTop: -2 }}>RISK CONSOLE</div></div>
    </div>
  );
}

function Spark({ d, color }: { d: string; color: string }) {
  return <svg width="60" height="26" viewBox="0 0 60 26" style={{ position: 'absolute', right: 14, bottom: 12 }}><path d={d} fill="none" stroke={color} strokeWidth="2" /></svg>;
}

const TITLES: Record<string, [string, string]> = {
  queue: ['Coordinated-abuse investigations', 'Live network monitoring — clusters scored, investigated and decided in real time.'],
  eval: ['Held-out evaluation', 'NEXUS vs. a naive structural rule, measured on a world the model never trained on.'],
  audit: ['Audit trail', 'Every scored cluster, investigation, decision and execution — fully logged.'],
};

export default function Page() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [ev, setEv] = useState<EvalResults | null>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [tab, setTab] = useState<'queue' | 'eval' | 'audit'>('queue');
  const [filter, setFilter] = useState<'rings' | 'all'>('rings');
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.overview().then(setOv).catch(() => setErr('Cannot reach the backend on :8000. Start it with ./run.sh'));
    api.cases().then(r => { setCases(r); const f = r.find(c => c.verdict === 'fraud_ring'); if (f) setSel(f.cluster_id); }).catch(() => {});
    api.evalResults().then(setEv).catch(() => {});
    api.audit().then(setAudit).catch(() => {});
  }, []);

  const shown = cases.filter(c => filter === 'all' || c.verdict === 'fraud_ring');
  const selRow = cases.find(c => c.cluster_id === sel);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '212px 1fr', minHeight: '100vh' }}>
      <aside style={{ padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: 24, position: 'sticky', top: 0, height: '100vh',
        background: 'linear-gradient(180deg,var(--navy-2),var(--navy))', borderRight: '1px solid var(--navy-3)' }}>
        <Logo />
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {([['queue', '◈  Investigations'], ['eval', '▤  Model evaluation'], ['audit', '≣  Audit log']] as const).map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)} style={{ textAlign: 'left', padding: '10px 12px', borderRadius: 9,
              border: '1px solid ' + (tab === k ? 'rgba(13,148,251,.35)' : 'transparent'), cursor: 'pointer',
              background: tab === k ? 'rgba(13,148,251,.16)' : 'transparent', color: tab === k ? '#fff' : '#9FB2CC',
              fontWeight: tab === k ? 700 : 500, fontSize: 13.5, transition: '.15s' }}>{l}</button>
          ))}
        </nav>
        <div style={{ marginTop: 'auto', fontSize: 10, color: '#6E86A8', lineHeight: 1.7 }}>
          {ov && <><span className="pulse-dot" /> live · seed {ov.seed}<br />{ov.accounts.toLocaleString()} accounts · {ov.transactions.toLocaleString()} txns<br /><span style={{ opacity: .6 }}>analyst engine online</span></>}
        </div>
      </aside>

      <main style={{ padding: '20px 26px', maxWidth: 1440 }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 18 }}>
          <div><h1 style={{ fontSize: 22, fontWeight: 800, margin: 0, letterSpacing: '-.02em' }}>{TITLES[tab][0]}</h1>
            <p style={{ color: 'var(--ink-3)', fontSize: 13, margin: '4px 0 0' }}>{TITLES[tab][1]}</p></div>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-2)', background: 'var(--panel)', border: '1px solid var(--brd)',
            padding: '6px 12px', borderRadius: 999, display: 'inline-flex', alignItems: 'center', gap: 7, boxShadow: 'var(--shadow)' }}>
            <span className="pulse-dot" /><Clock /></span>
        </header>

        {err && <div className="card" style={{ padding: 16, borderColor: 'var(--crit)', marginBottom: 18, color: 'var(--crit)' }}>{err}</div>}

        {ov && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 18 }}>
            <StatCard hero label="Exposure at risk" value={<CountUp value={ov.exposure_at_risk} money />} sub={`▲ ${ov.rings_confirmed} rings confirmed`} spark="M0 20 L10 16 L20 18 L30 9 L40 12 L50 4 L60 6" sparkColor="rgba(255,255,255,.7)" />
            <StatCard label="Exposure protected" value={<CountUp value={ov.exposure_protected} money />} sub="via bounded actions" color="var(--clear)" spark="M0 22 L12 18 L24 19 L36 10 L48 8 L60 3" sparkColor="var(--clear)" />
            <StatCard label="Auto-actioned" value={<CountUp value={ov.auto_actioned} />} sub={`${ov.human_review} to human review`} color="var(--brand)" spark="M0 18 L12 20 L24 12 L36 14 L48 6 L60 8" sparkColor="var(--brand)" />
            <StatCard label="Audit events" value={<CountUp value={ov.audit_events} />} sub="fully logged" spark="M0 16 L12 14 L24 16 L36 11 L48 12 L60 7" sparkColor="var(--ink-3)" />
          </div>
        )}

        {tab === 'queue' && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1.35fr 1fr', gap: 16, alignItems: 'start' }}>
              <div style={{ borderRadius: 18, overflow: 'hidden', background: 'radial-gradient(120% 120% at 30% 0%,#0C2444,#061529)',
                border: '1px solid var(--navy-3)', boxShadow: '0 18px 50px rgba(7,26,51,.4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 18px', borderBottom: '1px solid rgba(255,255,255,.07)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.09em', textTransform: 'uppercase', color: '#7E98BC' }}>
                    Relationship graph<b style={{ color: '#fff', fontSize: 14, display: 'block', letterSpacing: 0, textTransform: 'none', marginTop: 3 }}>
                      {selRow ? `${selRow.cluster_id} · ${selRow.n_accounts} linked accounts` : '—'}</b>
                  </div>
                  {selRow && badge(selRow.verdict)}
                </div>
                {sel && <CasePanel key={sel} clusterId={sel} graphOnly />}
                <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', padding: '0 18px 16px', fontSize: 10.5, color: '#7E98BC', fontWeight: 600 }}>
                  {[['#E5484D', 'Device'], ['#E08600', 'Card'], ['#7A5CFF', 'Address'], ['#0D94FB', 'IP'], ['#12B981', 'Timing']].map(([c, l]) => (
                    <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 6 }}><i style={{ width: 14, height: 3, borderRadius: 2, background: c }} />{l}</span>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="card" style={{ overflow: 'hidden' }}>
                  <div style={{ padding: 11, borderBottom: '1px solid var(--brd)', display: 'flex', gap: 6 }}>
                    {([['rings', 'Rings'], ['all', 'All clusters']] as const).map(([k, l]) => (
                      <button key={k} onClick={() => setFilter(k)} style={{ fontSize: 12, fontWeight: 600, padding: '6px 13px', borderRadius: 999, cursor: 'pointer',
                        border: '1px solid ' + (filter === k ? 'transparent' : 'var(--brd-2)'), background: filter === k ? 'var(--brand)' : 'transparent',
                        color: filter === k ? '#fff' : 'var(--ink-2)', boxShadow: filter === k ? '0 4px 12px var(--brand-glow)' : 'none' }}>{l}</button>
                    ))}
                  </div>
                  <div style={{ maxHeight: 328, overflowY: 'auto' }}>
                    {shown.map(c => (
                      <button key={c.cluster_id} onClick={() => setSel(c.cluster_id)} style={{ padding: '12px 15px', border: 'none', borderBottom: '1px solid var(--brd)',
                        borderLeft: '3px solid ' + (sel === c.cluster_id ? 'var(--brand)' : 'transparent'), background: sel === c.cluster_id ? 'var(--brand-wash)' : 'transparent',
                        width: '100%', textAlign: 'left', cursor: 'pointer', color: 'inherit', transition: '.15s' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink-2)' }}>{c.cluster_id}</span>{badge(c.verdict)}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                          <span className="tnum" style={{ fontWeight: 700, fontSize: 15 }}>{inr(c.exposure)}</span>
                          <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{c.n_accounts} accts · {Math.round(c.ring_probability * 100)}%</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="card" style={{ padding: '16px 18px' }}>
                  <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 12 }}>Live activity</div>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {shown.slice(0, 5).map((c, i) => {
                      const col = c.verdict === 'fraud_ring' ? 'var(--crit)' : 'var(--clear)';
                      return (
                        <div key={c.cluster_id} className="rise" style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '9px 0', borderBottom: '1px dashed var(--brd)', animationDelay: i * 90 + 'ms' }}>
                          <span style={{ width: 6, height: 6, borderRadius: 999, marginTop: 5, background: col, boxShadow: `0 0 8px ${col}` }} />
                          <div><div style={{ fontSize: 12.5 }}><b>{c.cluster_id} {c.verdict === 'fraud_ring' ? 'confirmed' : 'cleared'}</b></div>
                            <div style={{ fontSize: 11, color: 'var(--ink-3)' }}>{inr(c.exposure)} · {c.decision_action.replace(/_/g, ' ')}</div></div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
            <div style={{ marginTop: 16 }}>{sel && <CasePanel key={sel + '-full'} clusterId={sel} />}</div>
          </>
        )}

        {tab === 'eval' && ev && <EvalView ev={ev} />}

        {tab === 'audit' && (
          <div className="card rise" style={{ padding: '16px 18px' }}>
            <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 12 }}>Live audit trail</div>
            <div className="mono" style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '70vh', overflowY: 'auto' }}>
              {audit.length === 0 && <span style={{ color: 'var(--ink-3)' }}>No events.</span>}
              {audit.map((a, i) => (
                <div key={i} style={{ display: 'flex', gap: 12 }}>
                  <span style={{ color: 'var(--ink-3)' }}>{(a.ts || '').slice(11, 19)}</span>
                  <span style={{ color: 'var(--brand)', minWidth: 64 }}>{a.cluster_id}</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{a.event}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ hero, label, value, sub, color, spark, sparkColor }: any) {
  return (
    <div style={{ position: 'relative', padding: '16px 18px', borderRadius: 14, overflow: 'hidden',
      background: hero ? 'linear-gradient(135deg,#0D94FB,#0A6FC2)' : 'var(--panel)',
      border: '1px solid ' + (hero ? 'transparent' : 'var(--brd)'),
      boxShadow: hero ? '0 12px 34px rgba(13,148,251,.35)' : 'var(--shadow)' }}>
      <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: hero ? 'rgba(255,255,255,.85)' : 'var(--ink-3)' }}>{label}</div>
      <div className="tnum" style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-.02em', marginTop: 6, color: hero ? '#fff' : (color || 'var(--ink)') }}>{value}</div>
      <div style={{ fontSize: 11.5, marginTop: 4, color: hero ? 'rgba(255,255,255,.85)' : 'var(--ink-3)' }}>{sub}</div>
      <Spark d={spark} color={sparkColor} />
    </div>
  );
}

function EvalView({ ev }: { ev: EvalResults }) {
  const rows = [['baseline_structural', 'Naive structural rule'], ['nexus_ml_default', 'NEXUS (graph + ML)'], ['nexus_ml_tuned', 'NEXUS (tuned)']] as const;
  const bar = (v: number, col: string) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 7, background: '#E6EDF5', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${v * 100}%`, height: '100%', background: col, borderRadius: 4, transition: 'width .9s cubic-bezier(.2,.8,.2,1)' }} />
      </div>
      <span className="tnum" style={{ fontSize: 12.5, fontWeight: 700, minWidth: 38, textAlign: 'right' }}>{Math.round(v * 100)}%</span>
    </div>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="card rise" style={{ padding: '16px 18px' }}>
        <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 12 }}>Detection quality · held-out data</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5, minWidth: 640 }}>
            <thead><tr style={{ color: 'var(--ink-3)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em' }}>
              <th style={{ padding: 8 }}>Method</th><th style={{ padding: 8 }}>Precision</th><th style={{ padding: 8 }}>Recall</th>
              <th style={{ padding: 8, textAlign: 'right' }}>Evasive recall</th><th style={{ padding: 8, textAlign: 'right' }}>Customers wrongly hit</th>
            </tr></thead>
            <tbody>
              {rows.map(([k, label]) => {
                const m = ev.methods[k]; const isN = k !== 'baseline_structural';
                return (
                  <tr key={k} style={{ borderTop: '1px solid var(--brd)', background: k === 'nexus_ml_default' ? 'var(--brand-wash)' : 'transparent' }}>
                    <td style={{ padding: '12px 8px', fontWeight: isN ? 700 : 500 }}>{label}</td>
                    <td style={{ padding: '12px 8px', width: 150 }}>{bar(m.precision, 'var(--brand)')}</td>
                    <td style={{ padding: '12px 8px', width: 150 }}>{bar(m.recall, 'var(--brand-2)')}</td>
                    <td className="tnum" style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 700, color: m.recall_evasive < 0.5 ? 'var(--crit)' : 'var(--clear)' }}>{Math.round(m.recall_evasive * 100)}%</td>
                    <td className="tnum" style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 700, color: m.legit_accounts_hit > 10 ? 'var(--crit)' : 'var(--ink-2)' }}>{m.legit_accounts_hit}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 14, lineHeight: 1.6, maxWidth: 760 }}>
          The naive rule catches obvious rings but is <b style={{ color: 'var(--crit)' }}>blind to evasive rings</b> that rotate identifiers, and wrongly flags <b style={{ color: 'var(--crit)' }}>{ev.methods.baseline_structural.legit_accounts_hit} real customers</b>. NEXUS uses behavioural signal to catch both — and hits nearly none.
        </p>
      </div>
      <div className="card rise" style={{ padding: '16px 18px' }}>
        <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 12 }}>What the model weighs most</div>
        {Object.entries(ev.feature_importance).slice(0, 6).map(([k, v]) => (
          <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 9 }}>
            <span className="mono" style={{ fontSize: 12, minWidth: 170, color: 'var(--ink-2)' }}>{k}</span>
            <div style={{ flex: 1, height: 7, background: '#E6EDF5', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${v * 100}%`, height: '100%', background: 'linear-gradient(90deg,var(--brand),var(--brand-2))', borderRadius: 4 }} />
            </div>
            <span className="tnum" style={{ fontSize: 12, minWidth: 38, textAlign: 'right', color: 'var(--ink-3)' }}>{(v * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
