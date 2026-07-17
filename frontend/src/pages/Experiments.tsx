import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FlaskConical, Search, Trash2, RefreshCw,
  ChevronDown, ChevronUp, TrendingUp, Clock, Shield
} from 'lucide-react';
import { experimentsApi, trainingApi } from '../api/client';
import { StatusBadge, ProgressBar } from '../components/StatCard';
import { AccuracyChart, LossChart } from '../components/MetricsChart';
import type { Experiment, ExperimentDetail } from '../types';

export default function Experiments() {
  const navigate = useNavigate();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading]         = useState(true);
  const [search, setSearch]           = useState('');
  const [selected, setSelected]       = useState<ExperimentDetail | null>(null);
  const [detailLoading, setDL]        = useState(false);
  const [sortBy, setSortBy]           = useState<'created_at' | 'final_accuracy'>('created_at');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await experimentsApi.list(0, 100);
      setExperiments(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const hasRunning = experiments.some(e => e.status === 'running');
    if (!hasRunning) return;
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, [experiments, load]);

  async function openDetail(id: string) {
    setDL(true);
    try {
      const { data } = await experimentsApi.get(id);
      setSelected(data);
    } finally {
      setDL(false);
    }
  }

  async function deleteExp(id: string) {
    if (!confirm('Delete this experiment and all its metrics?')) return;
    await experimentsApi.delete(id);
    setExperiments(es => es.filter(e => e.id !== id));
    if (selected?.id === id) setSelected(null);
  }

  const filtered = experiments
    .filter(e => e.name.toLowerCase().includes(search.toLowerCase()) ||
                 e.algorithm.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'final_accuracy') {
        return (b.final_accuracy ?? 0) - (a.final_accuracy ?? 0);
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Experiment History</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {experiments.length} total experiments
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={load} className="btn-secondary flex items-center gap-2 text-sm">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={() => navigate('/training')} className="btn-primary flex items-center gap-2 text-sm">
            + New Experiment
          </button>
        </div>
      </div>

      {/* Search + Sort */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="Search by name or algorithm…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input w-48"
          value={sortBy}
          onChange={e => setSortBy(e.target.value as typeof sortBy)}
        >
          <option value="created_at">Sort: Newest</option>
          <option value="final_accuracy">Sort: Best Accuracy</option>
        </select>
      </div>

      <div className="flex gap-5">
        {/* Table */}
        <div className={`flex-1 card-glow overflow-hidden ${selected ? 'hidden lg:block' : ''}`}>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16">
              <FlaskConical size={40} className="text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">{search ? 'No results found' : 'No experiments yet'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1e293b]">
                    {['Name', 'Algorithm', 'Dataset', 'Status', 'Accuracy', 'Duration', ''].map(h => (
                      <th key={h} className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider pb-3 pr-3">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b]">
                  {filtered.map(exp => (
                    <tr
                      key={exp.id}
                      onClick={() => openDetail(exp.id)}
                      className={`hover:bg-[#1e293b]/60 transition-colors cursor-pointer ${selected?.id === exp.id ? 'bg-cyan-500/5' : ''}`}
                    >
                      <td className="py-3 pr-3">
                        <div>
                          <span className="font-medium text-slate-200 line-clamp-1">{exp.name}</span>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            {exp.dp_enabled && (
                              <span className="text-[10px] text-purple-400 font-mono">DP</span>
                            )}
                            {exp.sa_enabled && (
                              <span className="text-[10px] text-cyan-400 font-mono">SA</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 pr-3">
                        <span className="font-mono text-xs bg-[#1e293b] text-cyan-400 px-2 py-1 rounded">
                          {exp.algorithm.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 pr-3 text-slate-400 text-xs uppercase font-mono">
                        {exp.dataset}
                      </td>
                      <td className="py-3 pr-3">
                        <StatusBadge status={exp.status} />
                      </td>
                      <td className="py-3 pr-3">
                        <span className={`font-mono font-semibold text-sm ${exp.final_accuracy ? 'text-emerald-400' : 'text-slate-600'}`}>
                          {exp.final_accuracy != null ? `${(exp.final_accuracy * 100).toFixed(2)}%` : '—'}
                        </span>
                      </td>
                      <td className="py-3 pr-3 text-slate-500 text-xs">
                        {exp.duration_seconds != null
                          ? exp.duration_seconds < 60
                            ? `${exp.duration_seconds.toFixed(0)}s`
                            : `${(exp.duration_seconds / 60).toFixed(1)}m`
                          : '—'}
                      </td>
                      <td className="py-3">
                        <button
                          onClick={e => { e.stopPropagation(); deleteExp(exp.id); }}
                          className="text-slate-700 hover:text-red-400 transition-colors p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div className="w-full lg:w-[480px] flex-shrink-0 space-y-4">
            <div className="card-glow">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="font-semibold text-slate-200">{selected.name}</h2>
                  <p className="text-xs text-slate-500 mt-0.5 font-mono">{selected.id}</p>
                </div>
                <button onClick={() => setSelected(null)} className="text-slate-500 hover:text-slate-300 text-lg leading-none">✕</button>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs mb-4">
                {[
                  { k: 'Algorithm',   v: selected.algorithm.toUpperCase() },
                  { k: 'Dataset',     v: selected.dataset.toUpperCase()   },
                  { k: 'Model',       v: selected.model_type.toUpperCase()},
                  { k: 'Clients',     v: selected.num_clients              },
                  { k: 'Rounds',      v: selected.rounds                   },
                  { k: 'Epochs',      v: selected.local_epochs             },
                  { k: 'Batch Size',  v: selected.batch_size               },
                  { k: 'LR',          v: selected.learning_rate            },
                  { k: 'Partition',   v: selected.partition_method         },
                  { k: 'DP',          v: selected.dp_enabled ? 'Yes' : 'No'},
                  { k: 'Sec. Agg.',   v: selected.sa_enabled ? 'Yes' : 'No'},
                  { k: 'ε Total',     v: selected.total_epsilon != null ? selected.total_epsilon.toFixed(4) : '—' },
                ].map(({ k, v }) => (
                  <div key={k} className="flex justify-between border-b border-[#1e293b] pb-1.5">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-mono text-slate-300">{v}</span>
                  </div>
                ))}
              </div>

              {selected.status === 'completed' && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
                    <p className="text-xs text-slate-500 mb-1">Best Accuracy</p>
                    <p className="text-xl font-bold font-mono text-emerald-400">
                      {selected.best_accuracy != null ? `${(selected.best_accuracy * 100).toFixed(2)}%` : '—'}
                    </p>
                  </div>
                  <div className="bg-amber-500/10 rounded-lg p-3 text-center">
                    <p className="text-xs text-slate-500 mb-1">Final Loss</p>
                    <p className="text-xl font-bold font-mono text-amber-400">
                      {selected.final_loss != null ? selected.final_loss.toFixed(4) : '—'}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Mini Charts */}
            {selected.round_metrics.length > 0 && (
              <>
                <AccuracyChart
                  metrics={selected.round_metrics.map(m => ({
                    round: m.round_num, accuracy: m.accuracy * 100, loss: m.loss
                  }))}
                  totalRounds={selected.rounds}
                />
                <LossChart
                  metrics={selected.round_metrics.map(m => ({
                    round: m.round_num, accuracy: m.accuracy * 100, loss: m.loss
                  }))}
                  totalRounds={selected.rounds}
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
