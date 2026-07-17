import { useState, useEffect } from 'react';
import {
  Shield, Lock, Eye, EyeOff, AlertTriangle,
  CheckCircle2, Info, TrendingUp
} from 'lucide-react';
import { privacyApi, experimentsApi } from '../api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { ProgressBar } from '../components/StatCard';
import type { Experiment } from '../types';

interface BudgetData {
  experiment_id:   string;
  dp_enabled:      boolean;
  total_epsilon:   number | null;
  target_epsilon:  number | null;
  rounds_logged:   number;
  history: { round: number; epsilon_round: number; epsilon_total: number; delta: number }[];
}

interface OverviewData {
  total_dp_experiments:     number;
  total_epsilon_consumed:   number;
  avg_epsilon_per_run:      number;
  completed_dp_experiments: number;
}

const FALLBACK_MAX_EPSILON = 10;

export default function Privacy() {
  const [overview, setOverview]         = useState<OverviewData | null>(null);
  const [dpExps, setDPExps]             = useState<Experiment[]>([]);
  const [selectedBudget, setSelBudget]  = useState<BudgetData | null>(null);
  const [loading, setLoading]           = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [ovRes, exRes] = await Promise.all([
          privacyApi.overview(),
          experimentsApi.list(0, 50),
        ]);
        setOverview(ovRes.data);
        setDPExps(exRes.data.filter((e: Experiment) => e.dp_enabled));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function selectExp(id: string) {
    const { data } = await privacyApi.budget(id);
    setSelBudget(data);
  }

  const MAX_EPSILON = selectedBudget?.target_epsilon ?? FALLBACK_MAX_EPSILON;

  const budgetPct = selectedBudget?.total_epsilon
    ? Math.min((selectedBudget.total_epsilon / MAX_EPSILON) * 100, 100)
    : 0;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3 text-xs shadow-xl">
        <p className="text-slate-400 mb-1">Round {label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} className="font-mono" style={{ color: p.color }}>
            {p.dataKey === 'epsilon_total' ? 'ε cumulative' : 'ε this round'}: {p.value?.toFixed(6)}
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100">Privacy Monitor</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Track differential privacy budget consumption across experiments.
        </p>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'DP Experiments',   value: overview.total_dp_experiments,   color: 'text-purple-400', icon: Lock },
            { label: 'Total ε Consumed', value: overview.total_epsilon_consumed.toFixed(4), color: 'text-amber-400', icon: TrendingUp },
            { label: 'Avg ε per Run',    value: overview.avg_epsilon_per_run.toFixed(4),    color: 'text-cyan-400',   icon: Eye },
            { label: 'Completed (DP)',   value: overview.completed_dp_experiments, color: 'text-emerald-400', icon: CheckCircle2 },
          ].map(({ label, value, color, icon: Icon }) => (
            <div key={label} className="card-glow flex items-start gap-3">
              <div className="bg-[#1e293b] rounded-lg p-2">
                <Icon size={16} className={color} />
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">{label}</p>
                <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* DP Experiment List */}
        <div className="card-glow">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Shield size={14} /> DP Experiments
          </h2>
          {loading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-14 bg-[#1e293b] rounded-lg animate-pulse" />
              ))}
            </div>
          ) : dpExps.length === 0 ? (
            <div className="text-center py-8">
              <EyeOff size={32} className="text-slate-700 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">No DP experiments yet</p>
              <p className="text-slate-600 text-xs mt-1">Enable DP in the Training form</p>
            </div>
          ) : (
            <div className="space-y-2">
              {dpExps.map(exp => (
                <button
                  key={exp.id}
                  onClick={() => selectExp(exp.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    selectedBudget?.experiment_id === exp.id
                      ? 'bg-purple-500/10 border-purple-500/30'
                      : 'bg-[#1e293b] border-transparent hover:border-[#334155]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-200 truncate">{exp.name}</span>
                    <span className={`text-xs font-mono ${exp.total_epsilon ? 'text-amber-400' : 'text-slate-600'}`}>
                      {exp.total_epsilon != null ? `ε=${exp.total_epsilon.toFixed(2)}` : '—'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-600 font-mono">{exp.algorithm.toUpperCase()}</span>
                    {exp.noise_mult != null && (
                      <span className="text-xs text-slate-600">σ={exp.noise_mult}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Budget Detail */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedBudget ? (
            <div className="card-glow flex flex-col items-center justify-center py-16 text-center">
              <Shield size={40} className="text-slate-700 mb-3" />
              <p className="text-slate-500">Select an experiment to view its privacy budget</p>
            </div>
          ) : (
            <>
              {/* Budget gauge */}
              <div className="card-glow">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-slate-300">Privacy Budget Consumption</h3>
                  {budgetPct >= 80 && (
                    <div className="flex items-center gap-1.5 text-amber-400 text-xs">
                      <AlertTriangle size={14} />
                      High budget usage
                    </div>
                  )}
                </div>

                <div className="flex items-end gap-4 mb-4">
                  <div>
                    <p className="text-4xl font-bold font-mono text-purple-400">
                      ε = {selectedBudget.total_epsilon?.toFixed(4) ?? '0'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      of {MAX_EPSILON} max budget · {selectedBudget.rounds_logged} rounds tracked
                    </p>
                  </div>
                </div>

                <ProgressBar
                  value={budgetPct}
                  label={`Budget Used — ${budgetPct.toFixed(1)}%`}
                />
                <div className="flex justify-between text-xs text-slate-600 mt-1.5">
                  <span>ε = 0</span>
                  <span>ε = {MAX_EPSILON} (exhausted)</span>
                </div>
              </div>

              {/* Epsilon accumulation chart */}
              {selectedBudget.history.length > 0 && (
                <div className="card-glow">
                  <h3 className="text-sm font-semibold text-slate-300 mb-4">ε Accumulation per Round</h3>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={selectedBudget.history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="round" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#1e293b' }} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#1e293b' }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="epsilon_total" stroke="#a855f7" strokeWidth={2} dot={false} name="ε cumulative" />
                      <Line type="monotone" dataKey="epsilon_round" stroke="#6366f1" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="ε per round" />
                      <ReferenceLine y={MAX_EPSILON} stroke="#ef4444" strokeDasharray="4 2" label={{ value: 'MAX', fill: '#ef4444', fontSize: 10 }} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex gap-4 mt-2 text-xs justify-center">
                    <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-purple-500 inline-block" /> Cumulative ε</span>
                    <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-indigo-500 inline-block border-dashed" /> Per-round ε</span>
                    <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-red-500 inline-block" /> Budget limit</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Algorithm explanations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          {
            title: 'Differential Privacy — Gaussian Mechanism',
            icon: Shield, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20',
            points: [
              'Clips each client\'s weight update to L2 norm ≤ C (max_grad_norm)',
              'Adds Gaussian noise N(0, σ²C²) to the clipped update',
              'Each round consumes ε ≈ q·√(2·ln(1.25/δ))/σ',
              'Privacy budget accumulates across rounds by composition',
            ],
          },
          {
            title: 'Secure Aggregation — Additive Masking',
            icon: Lock, color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20',
            points: [
              'Client i generates random masks r_ij for every client j',
              'Each client adds outgoing masks and subtracts incoming masks',
              'All masks cancel during server-side aggregation',
              'Server learns only the sum — individual updates stay private',
            ],
          },
        ].map(({ title, icon: Icon, color, bg, points }) => (
          <div key={title} className={`card border ${bg}`}>
            <h3 className={`text-sm font-semibold mb-3 flex items-center gap-2 ${color}`}>
              <Icon size={15} /> {title}
            </h3>
            <ul className="space-y-2">
              {points.map((p, i) => (
                <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                  <span className={`font-mono ${color} mt-0.5`}>{i + 1}.</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
