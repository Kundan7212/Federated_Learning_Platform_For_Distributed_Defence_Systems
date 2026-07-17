import { TrendingUp, type LucideIcon } from 'lucide-react';
import type { ExperimentStatus } from '../types';
import clsx from 'clsx';

const STATUS_DOT: Record<ExperimentStatus, string> = {
  running:   'bg-cyan-400 animate-pulse',
  completed: 'bg-emerald-400',
  failed:    'bg-red-400',
  pending:   'bg-amber-400',
  cancelled: 'bg-slate-400',
};

const STATUS_CLASS: Record<ExperimentStatus, string> = {
  running:   'badge-running',
  completed: 'badge-completed',
  failed:    'badge-failed',
  pending:   'badge-pending',
  cancelled: 'badge-cancelled',
};

export function StatusBadge({ status }: { status: ExperimentStatus }) {
  return (
    <span className={STATUS_CLASS[status]}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', STATUS_DOT[status])} />
      {status.toUpperCase()}
    </span>
  );
}

interface StatCardProps {
  label:    string;
  value:    string | number;
  icon:     LucideIcon;
  color?:   'cyan' | 'emerald' | 'amber' | 'purple';
  suffix?:  string;
  sub?:     string;
}

const COLOR_MAP = {
  cyan:    { icon: 'text-cyan-400',    bg: 'bg-cyan-500/10',    border: 'border-cyan-500/20'    },
  emerald: { icon: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
  amber:   { icon: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/20'   },
  purple:  { icon: 'text-purple-400',  bg: 'bg-purple-500/10',  border: 'border-purple-500/20'  },
};

export function StatCard({ label, value, icon: Icon, color = 'cyan', suffix, sub }: StatCardProps) {
  const c = COLOR_MAP[color];
  return (
    <div className="card-glow flex items-start gap-4">
      <div className={clsx('p-2.5 rounded-lg border', c.bg, c.border)}>
        <Icon size={20} className={c.icon} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-2xl font-bold font-mono text-slate-100">
          {value}
          {suffix && <span className="text-base font-medium text-slate-400 ml-1">{suffix}</span>}
        </p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  return (
    <div>
      {label && (
        <div className="flex justify-between text-xs mb-1.5">
          <span className="text-slate-400">{label}</span>
          <span className="text-cyan-400 font-mono">{value.toFixed(1)}%</span>
        </div>
      )}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}
