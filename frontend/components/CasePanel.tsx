'use client';
import React, { useEffect, useState } from 'react';
import { api, inr, CaseDetail, GraphData } from '@/lib/api';
import RingGraph from './RingGraph';

const ACT: Record<string, string> = { step_up_all: 'Step-up verify all', step_up_topk: 'Step-up top-risk', block_all: 'Block all', block_topk: 'Block top-risk', monitor: 'Monitor', clear: 'Clear — no action', human_review: 'Escalate to human' };

function label(v: string) {
  const m: Record<string, string> = { fraud_ring: 'Fraud ring', office: 'Office', family: 'Family', reseller: 'Reseller', inconclusive: 'Inconclusive' };
  return m[v] || v;
}

export default function CasePanel({ clusterId, graphOnly }: { clusterId: string; graphOnly?: boolean }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [executed, setExecuted] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null); setGraph(null); setExecuted(null);
    api.case(clusterId).then(setDetail);
    api.graph(clusterId).then(setGraph);
  }, [clusterId]);

  if (graphOnly) {
    if (!graph || !detail) return <div style={{ height: 400 }} />;
    return <RingGraph data={graph} verdict={detail.case_file.verdict} />;
  }

  if (!detail) return null;
  const cf = detail.case_file, ev = detail.evidence, dec = detail.decision;
  const factById = Object.fromEntries(ev.facts.map(f => [f.fact_id, f]));
  const pct = Math.round(detail.ring_probability * 100);
  const rc = detail.ring_probability > .6 ? 'var(--crit)' : detail.ring_probability > .3 ? 'var(--warn)' : 'var(--clear)';
  const C = 2 * Math.PI * 27;
  const factBg = (d: string) => d === 'incriminating' ? 'var(--crit-wash)' : d === 'exculpatory' ? 'var(--clear-wash)' : '#F1F5FA';
  const factFg = (d: string) => d === 'incriminating' ? 'var(--crit)' : d === 'exculpatory' ? 'var(--clear)' : 'var(--ink-2)';

  const runExecute = async () => { const r = await api.execute(clusterId); setExecuted(r.executed ? 'Executed — action recorded ✓' : `No-op — ${r.reason}`); };
  const clabel = (t: string) => <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 12 }}>{t}</div>;

  return (
    <div className="rise" style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
      <div className="card" style={{ padding: '16px 18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: 70, height: 70, flex: 'none' }}>
            <svg width="70" height="70" viewBox="0 0 70 70"><circle cx="35" cy="35" r="27" fill="none" stroke="#E6EDF5" strokeWidth="6" />
              <circle cx="35" cy="35" r="27" fill="none" stroke={rc} strokeWidth="6" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - detail.ring_probability)} transform="rotate(-90 35 35)" /></svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16, color: rc }}>{pct}</div>
          </div>
          <div style={{ flex: 1, minWidth: 240, fontSize: 14, color: 'var(--ink-2)', lineHeight: 1.5 }}>
            <div style={{ display: 'flex', gap: 9, alignItems: 'center', marginBottom: 5 }}>
              <span className="mono" style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>{clusterId}</span>
              <span style={{ fontSize: 13, fontWeight: 700 }}>{label(cf.verdict)}</span>
              {cf.grounded && <span style={{ fontSize: 11, color: 'var(--clear)', fontWeight: 600 }}>✓ grounded</span>}
            </div>{cf.narrative}
          </div>
          <div style={{ textAlign: 'right' }}>
            <b className="tnum" style={{ fontSize: 22 }}>{inr(detail.recommended.total_exposure)}</b>
            <span style={{ display: 'block', fontSize: 11.5, color: 'var(--ink-3)', marginTop: 2 }}>{ev.n_accounts} accounts · conf {cf.confidence}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15 }}>
        <div className="card" style={{ padding: '16px 18px' }}>{clabel('Evidence · clickable ground truth')}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 250, overflowY: 'auto' }}>
            {ev.facts.map(f => (
              <div key={f.fact_id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '9px 11px', borderRadius: 9, background: factBg(f.direction) }}>
                <span className="mono" style={{ fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 5, whiteSpace: 'nowrap', color: factFg(f.direction), background: 'color-mix(in srgb, ' + factFg(f.direction) + ' 14%, transparent)' }}>{f.fact_id}</span>
                <span style={{ fontSize: 12.5, lineHeight: 1.4 }}>{f.statement}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card" style={{ padding: '16px 18px' }}>{clabel('Intervention options · minimum defensible highlighted')}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr style={{ color: 'var(--ink-3)', textAlign: 'left', fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '.05em' }}>
                <th style={{ padding: '6px 8px' }}>Action</th><th style={{ padding: '6px 8px', textAlign: 'right' }}>Protected</th><th style={{ padding: '6px 8px', textAlign: 'right' }}>Friction</th><th style={{ padding: '6px 8px', textAlign: 'right' }}>Legit hit</th>
              </tr></thead>
              <tbody>
                {detail.interventions.map(iv => {
                  const rec = iv.action === detail.recommended.action;
                  return (
                    <tr key={iv.action} style={{ background: rec ? 'var(--brand-wash)' : 'transparent', borderTop: '1px solid var(--brd)' }}>
                      <td style={{ padding: '9px 8px', fontWeight: rec ? 700 : 500 }}>{rec && <span style={{ color: 'var(--brand)', marginRight: 6 }}>▶</span>}{ACT[iv.action] || iv.action}</td>
                      <td className="tnum" style={{ padding: '9px 8px', textAlign: 'right' }}>{Math.round(iv.risk_reduced_pct * 100)}%</td>
                      <td className="tnum" style={{ padding: '9px 8px', textAlign: 'right' }}>{iv.friction_cost.toFixed(1)}</td>
                      <td className="tnum" style={{ padding: '9px 8px', textAlign: 'right', color: iv.legit_accounts_hit > 0 ? 'var(--crit)' : 'var(--ink-3)' }}>{iv.legit_accounts_hit}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15 }}>
        <div className="card" style={{ padding: '16px 18px' }}>{clabel('Case for a ring')}
          {cf.reasons_for.length === 0 ? <div style={{ color: 'var(--ink-3)', fontSize: 13 }}>None.</div> : cf.reasons_for.map((r, i) => (
            <div key={i} style={{ marginBottom: 10, fontSize: 13, lineHeight: 1.5 }}>{r.point}
              <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>{r.fact_ids.map(id => <b key={id} title={factById[id]?.statement} className="mono" style={{ fontSize: 9.5, padding: '1px 6px', borderRadius: 5, color: 'var(--crit)', background: 'var(--crit-wash)' }}>{id}</b>)}</div>
            </div>
          ))}
        </div>
        <div className="card" style={{ padding: '16px 18px' }}>{clabel('Case against')}
          {cf.reasons_against.length === 0 ? <div style={{ color: 'var(--ink-3)', fontSize: 13 }}>None.</div> : cf.reasons_against.map((r, i) => (
            <div key={i} style={{ marginBottom: 10, fontSize: 13, lineHeight: 1.5 }}>{r.point}
              <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>{r.fact_ids.map(id => <b key={id} title={factById[id]?.statement} className="mono" style={{ fontSize: 9.5, padding: '1px 6px', borderRadius: 5, color: 'var(--clear)', background: 'var(--clear-wash)' }}>{id}</b>)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: '16px 18px', border: '1.5px solid ' + (dec.authorized ? 'var(--clear)' : 'var(--warn)') }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>{clabel('Policy decision')}
            <div style={{ fontSize: 15.5, fontWeight: 700 }}>{dec.authorized
              ? <>Authorized: <span style={{ color: 'var(--brand)' }}>{ACT[dec.action] || dec.action}</span></>
              : <>Held for review: <span style={{ color: 'var(--warn)' }}>{ACT[dec.action] || dec.action}</span></>}</div>
            {dec.stopped_reason && <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 3 }}>{dec.stopped_reason}</div>}
          </div>
          <button onClick={runExecute} disabled={!dec.authorized} style={{ padding: '11px 22px', borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: dec.authorized ? 'pointer' : 'not-allowed',
            border: 'none', color: dec.authorized ? '#fff' : 'var(--ink-3)', background: dec.authorized ? 'var(--brand)' : '#E3EAF2', boxShadow: dec.authorized ? '0 6px 16px var(--brand-glow)' : 'none' }}>Execute action</button>
        </div>
        {executed && <div style={{ marginTop: 10, fontSize: 13, color: 'var(--clear)', fontWeight: 600 }}>{executed}</div>}
        <div style={{ marginTop: 13, display: 'flex', flexDirection: 'column', gap: 5 }}>
          {dec.reason_checks.map((c, i) => <div key={i} className="mono" style={{ fontSize: 11.5, color: c.startsWith('✓') ? 'var(--ink-2)' : 'var(--crit)' }}>{c}</div>)}
        </div>
      </div>
    </div>
  );
}
