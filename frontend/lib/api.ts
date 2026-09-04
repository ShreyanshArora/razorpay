export interface Overview {
  world: string; seed: number; accounts: number; transactions: number;
  clusters_detected: number; rings_confirmed: number;
  exposure_at_risk: number; exposure_protected: number;
  auto_actioned: number; human_review: number; audit_events: number;
}
export interface CaseRow {
  cluster_id: string; verdict: string; confidence: number; ring_probability: number;
  n_accounts: number; exposure: number; recommended_action: string;
  authorized: boolean; decision_action: string; provider: string; narrative: string;
}
export interface Fact {
  fact_id: string; kind: string; statement: string; weight: string;
  direction: string; evidence: Record<string, any>;
}
export interface Reason { fact_ids: string[]; point: string; }
export interface Intervention {
  action: string; target_accounts: string[]; exposure_protected: number;
  total_exposure: number; risk_reduced_pct: number; friction_cost: number;
  legit_accounts_hit: number; meets_target: boolean;
}
export interface CaseDetail {
  cluster_id: string; ring_probability: number;
  case_file: {
    verdict: string; confidence: number; narrative: string; provider: string;
    grounded: boolean; recommended_posture: string;
    reasons_for: Reason[]; reasons_against: Reason[]; dropped_citations: string[];
  };
  evidence: { n_accounts: number; ring_probability: number; facts: Fact[]; feature_snapshot: Record<string, number>; };
  interventions: Intervention[];
  recommended: Intervention;
  decision: {
    decision_id: string; authorized: boolean; action: string; target_accounts: string[];
    reason_checks: string[]; stopped_reason: string | null; verdict: string;
    confidence: number; ring_probability: number;
  };
}
export interface GraphData {
  cluster_id: string;
  nodes: { id: string; exposure: number }[];
  edges: { source: string; target: string; kinds: string[]; weight: number }[];
}
export interface EvalResults {
  tuned_threshold: number;
  feature_importance: Record<string, number>;
  test_summary: Record<string, any>;
  methods: Record<string, {
    method: string; precision: number; recall: number; f1: number;
    recall_obvious: number; recall_evasive: number; fp: number;
    legit_accounts_hit: number; tp: number; fn: number;
  }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
const j = async (u: string, o?: RequestInit) => {
  u = API_BASE + u;
  const r = await fetch(u, o); if (!r.ok) throw new Error(`${u} ${r.status}`); return r.json();
};
export const api = {
  overview: (): Promise<Overview> => j('/api/overview'),
  cases: (): Promise<CaseRow[]> => j('/api/cases'),
  case: (id: string): Promise<CaseDetail> => j(`/api/cases/${id}`),
  graph: (id: string): Promise<GraphData> => j(`/api/cases/${id}/graph`),
  evalResults: (): Promise<EvalResults> => j('/api/eval'),
  execute: (id: string) => j(`/api/cases/${id}/execute`, { method: 'POST' }),
  audit: (): Promise<any[]> => j('/api/audit'),
};
export const inr = (n: number) => {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)}L`;
  if (n >= 1e3) return `₹${(n / 1e3).toFixed(1)}K`;
  return `₹${n.toFixed(0)}`;
};
