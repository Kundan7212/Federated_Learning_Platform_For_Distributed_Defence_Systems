import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FlaskConical, Play, Shield, TrendingUp,
  ChevronRight, RefreshCw, Activity, Lock
} from 'lucide-react';
import { metricsApi } from '../api/client';
import { StatCard, StatusBadge } from '../components/StatCard';
import type { DashboardStats } from '../types';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats]     = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  async function fetchStats() {
    setLoading(true);
    try {
      const { data } = await metricsApi.dashboard();
      setStats(data);
      setError('');
    } catch {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchStats(); }, []);

  useEffect(() => {
    if (!stats?.running_count) return;
    const id = setInterval(fetchStats, 10_000);
    return () => clearInterval(id);
  }, [stats?.running_count]);

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Intelligence Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5 font-mono">
            FEDERATED LEARNING COMMAND CENTER
          </p>
        </div>
        <div className="flex items-center gap-3">
          {stats?.running_count ? (
            <span className="badge-running">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              {stats.running_count} TRAINING ACTIVE
            </span>
          ) : null}
          <button
            onClick={fetchStats}
            className="btn-secondary flex items-center gap-2 text-sm"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={() => navigate('/training')}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Play size={14} /> New Experiment
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Stats Grid */}
      {loading && !stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-28 animate-pulse bg-[#0f172a]" />
          ))}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Experiments"
            value={stats.total_experiments}
            icon={FlaskConical}
            color="cyan"
            sub={`${stats.completed_count} completed`}
          />
          <StatCard
            label="Best Accuracy"
            value={stats.best_accuracy.toFixed(2)}
            icon={TrendingUp}
            color="emerald"
            suffix="%"
            sub={`avg ${stats.avg_accuracy.toFixed(2)}%`}
          />
          <StatCard
            label="Active Training"
            value={stats.running_count}
            icon={Activity}
            color="amber"
            sub="live experiments"
          />
          <StatCard
            label="Privacy-Enabled"
            value={stats.dp_experiments}
            icon={Lock}
            color="purple"
            sub={`${stats.total_rounds} total rounds`}
          />
        </div>
      ) : null}

      {/* Recent Experiments */}
      <div className="card-glow">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            Recent Experiments
          </h2>
          <button
            onClick={() => navigate('/experiments')}
            className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            View all <ChevronRight size={12} />
          </button>
        </div>

        {!stats?.recent_experiments?.length ? (
          <div className="text-center py-12">
            <FlaskConical size={40} className="text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No experiments yet</p>
            <button
              onClick={() => navigate('/training')}
              className="btn-primary mt-4 text-sm"
            >
              Start Your First Experiment
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-[#1e293b]">
                  {['Name', 'Algorithm', 'Status', 'Accuracy', 'Started'].map(h => (
                    <th key={h} className="text-xs font-medium text-slate-500 uppercase tracking-wider pb-3 pr-4">
                      {h}
                    </th>
                  ))}
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]">
                {stats.recent_experiments.map(exp => (
                  <tr
                    key={exp.id}
                    className="hover:bg-[#1e293b]/50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/experiments`)}
                  >
                    <td className="py-3 pr-4">
                      <span className="font-medium text-slate-200">{exp.name}</span>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="font-mono text-xs bg-[#1e293b] text-cyan-400 px-2 py-1 rounded">
                        {exp.algorithm.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={exp.status} />
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`font-mono font-semibold ${exp.final_accuracy ? 'text-emerald-400' : 'text-slate-600'}`}>
                        {exp.final_accuracy != null ? `${exp.final_accuracy.toFixed(2)}%` : '—'}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-500 text-xs">
                      {new Date(exp.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3">
                      <ChevronRight size={14} className="text-slate-600" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            title: 'FedAvg Training',
            desc:  'Standard synchronous federated averaging. Best starting point.',
            color: 'cyan',
            onClick: () => navigate('/training'),
          },
          {
            title: 'Privacy-Preserving',
            desc:  'Enable differential privacy with Gaussian noise mechanism.',
            color: 'purple',
            onClick: () => navigate('/training'),
          },
          {
            title: 'Privacy Monitor',
            desc:  'Track epsilon-delta budget consumption across experiments.',
            color: 'emerald',
            onClick: () => navigate('/privacy'),
          },
        ].map(({ title, desc, color, onClick }) => (
          <button
            key={title}
            onClick={onClick}
            className="card-glow text-left hover:border-cyan-500/30 transition-all duration-200 group"
          >
            <h3 className={`text-sm font-semibold mb-1.5 ${color === 'cyan' ? 'text-cyan-400' : color === 'purple' ? 'text-purple-400' : 'text-emerald-400'} group-hover:brightness-125`}>
              {title}
            </h3>
            <p className="text-xs text-slate-500">{desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
