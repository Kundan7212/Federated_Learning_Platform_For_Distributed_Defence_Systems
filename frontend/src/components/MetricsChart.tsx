import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart,
} from 'recharts';
import type { LiveMetric } from '../hooks/useWebSocket';

interface Props {
  metrics: LiveMetric[];
  totalRounds: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">Round {label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} style={{ color: entry.color }} className="font-mono">
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(4) : entry.value}
        </p>
      ))}
    </div>
  );
};

export function AccuracyChart({ metrics, totalRounds }: Props) {
  const data = metrics.map(m => ({
    round:    m.round,
    accuracy: parseFloat(m.accuracy.toFixed(4)),
  }));

  return (
    <div className="card-glow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300">Global Accuracy</h3>
        {metrics.length > 0 && (
          <span className="text-xl font-bold font-mono text-emerald-400">
            {metrics[metrics.length - 1].accuracy.toFixed(2)}%
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="round"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e293b' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e293b' }}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="accuracy"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#accGrad)"
            dot={false}
            activeDot={{ r: 4, fill: '#10b981', stroke: '#0f172a', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LossChart({ metrics, totalRounds }: Props) {
  const data = metrics.map(m => ({
    round: m.round,
    loss:  parseFloat(m.loss.toFixed(6)),
  }));

  return (
    <div className="card-glow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300">Global Loss</h3>
        {metrics.length > 0 && (
          <span className="text-xl font-bold font-mono text-amber-400">
            {metrics[metrics.length - 1].loss.toFixed(4)}
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="round"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e293b' }}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e293b' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="loss"
            stroke="#f59e0b"
            strokeWidth={2}
            fill="url(#lossGrad)"
            dot={false}
            activeDot={{ r: 4, fill: '#f59e0b', stroke: '#0f172a', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EpsilonChart({ metrics }: { metrics: LiveMetric[] }) {
  const data = metrics
    .filter(m => m.epsilon !== undefined)
    .map(m => ({ round: m.round, epsilon: parseFloat((m.epsilon ?? 0).toFixed(4)) }));

  if (data.length === 0) return null;

  return (
    <div className="card-glow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300">Privacy Budget (ε)</h3>
        <span className="text-xl font-bold font-mono text-purple-400">
          ε = {data[data.length - 1].epsilon.toFixed(4)}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="round" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#1e293b' }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#1e293b' }} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="epsilon" stroke="#a855f7" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
