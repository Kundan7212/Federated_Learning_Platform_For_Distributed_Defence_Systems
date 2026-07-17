import { useState } from 'react';
import {
  BookOpen, Network, GitMerge, Clock, Layers,
  ChevronRight, FileText, ListOrdered, Sigma, Info,
} from 'lucide-react';
import clsx from 'clsx';

interface AlgoDoc {
  id: string;
  label: string;
  type: 'synchronous' | 'asynchronous';
  color: 'cyan' | 'emerald' | 'amber' | 'purple';
  intuition: string;
  formulas: { label: string; expr: string }[];
  variables: { symbol: string; meaning: string }[];
  workflow: string[];
}

const ALGO_DOCS: AlgoDoc[] = [
  {
    id: 'fedavg',
    label: 'FedAvg',
    type: 'synchronous',
    color: 'cyan',
    intuition:
      "Every round, all clients start from the same global model, train locally for a few epochs on their own data, " +
      "and send back their updated weights. The server combines them into a single new global model by averaging, " +
      "weighting each client in proportion to how much data it trained on. Clients with more data get more say — " +
      "a client with 900 samples influences the average 90x more than a client with 10 samples.",
    formulas: [
      { label: 'Local training (unchanged, per client k)', expr: 'w_k^(t+1) = LocalSGD(w_t, D_k)  for E local epochs' },
      { label: 'Weighted aggregation', expr: 'w_(t+1) = Σ_k  (n_k / n) · w_k^(t+1)' },
    ],
    variables: [
      { symbol: 'w_t', meaning: 'Global model weights at round t' },
      { symbol: 'w_k^(t+1)', meaning: "Client k's locally-trained weights after round t" },
      { symbol: 'D_k', meaning: "Client k's local dataset" },
      { symbol: 'n_k', meaning: "Client k's number of local samples" },
      { symbol: 'n', meaning: 'Σ_k n_k — total samples across all participating clients' },
      { symbol: 'E', meaning: 'Local epochs per round (local_epochs)' },
    ],
    workflow: [
      'Server broadcasts the current global weights w_t to every client.',
      'Every client trains locally for E epochs (plain cross-entropy SGD) starting from w_t.',
      'Every client sends its updated weights w_k^(t+1) and its sample count n_k back to the server.',
      'Server computes the sample-weighted average of all client weights → w_(t+1).',
      'Repeat for the configured number of rounds.',
    ],
  },
  {
    id: 'fedprox',
    label: 'FedProx',
    type: 'synchronous',
    color: 'purple',
    intuition:
      "FedProx is FedAvg with one change to local training: it adds a proximal penalty term that discourages a " +
      "client's local model from drifting too far from the global model it started from. On non-IID data, " +
      "clients can otherwise pull the model strongly toward their own local optimum; the μ term acts like a " +
      "leash, trading off local progress for global consistency. Aggregation itself is unchanged from FedAvg — " +
      "the same sample-weighted average of client weights.",
    formulas: [
      { label: 'Local objective (replaces plain cross-entropy loss)', expr: 'h_k(w; w_t) = F_k(w) + (μ/2) · ‖w − w_t‖²' },
      { label: 'Local training', expr: 'w_k^(t+1) = LocalSGD(w_t, D_k, h_k)  for E local epochs' },
      { label: 'Aggregation (identical to FedAvg)', expr: 'w_(t+1) = Σ_k  (n_k / n) · w_k^(t+1)' },
    ],
    variables: [
      { symbol: 'F_k(w)', meaning: "Client k's plain local loss (cross-entropy)" },
      { symbol: 'μ', meaning: 'Proximal term strength (fedprox_mu, default 0.01) — how strongly local training is pulled back toward w_t' },
      { symbol: '‖w − w_t‖²', meaning: 'Squared L2 distance between the local model being trained and the global model it started from' },
      { symbol: 'w_t, n_k, n, E', meaning: 'Same meaning as in FedAvg' },
    ],
    workflow: [
      'Server broadcasts the current global weights w_t to every client.',
      'Each client trains locally for E epochs, minimizing F_k(w) + (μ/2)‖w − w_t‖² instead of plain F_k(w).',
      'The proximal term is recomputed every batch against the frozen w_t the client started from.',
      'Every client sends back w_k^(t+1) and n_k, exactly as in FedAvg.',
      'Server aggregates with the same sample-weighted average as FedAvg → w_(t+1).',
    ],
  },
  {
    id: 'fedasync',
    label: 'FedAsync',
    type: 'asynchronous',
    color: 'amber',
    intuition:
      "Instead of waiting for every client to finish before updating the model (which wastes time waiting on the " +
      "slowest client), FedAsync updates the global model the moment any single client finishes — a fast phone " +
      "updates the model many times while a slow one is still training its first round. Because a client may be " +
      "training against a global model that's since moved on (staleness), its contribution is shrunk the more " +
      "stale it is, so a wildly out-of-date update can't knock the global model off course.",
    formulas: [
      { label: 'Local training (client k, dispatched at global version τ)', expr: 'w_k = LocalSGD(w_τ, D_k)' },
      { label: 'Staleness', expr: 's = t − τ' },
      { label: 'Staleness weighting function ("inverse" mode)', expr: 'f(s) = 1 / (1 + s)' },
      { label: 'Effective mixing coefficient', expr: 'α_eff = α · f(s)' },
      { label: 'Global update — convex combination', expr: 'w_(t+1) = (1 − α_eff) · w_t + α_eff · w_k' },
    ],
    variables: [
      { symbol: 'τ', meaning: 'Global model version the client started training from (start_version)' },
      { symbol: 't', meaning: 'Current global version at the moment this update arrives' },
      { symbol: 's = t − τ', meaning: "Staleness — how many global updates have happened since this client's copy was handed out" },
      { symbol: 'α', meaning: 'Base mixing coefficient (async_alpha)' },
      { symbol: 'f(s)', meaning: 'Staleness discount — 1 when s=0 (fresh), shrinking toward 0 as s grows (staleness_weighting="inverse"); f(s)=1 for every s if staleness_weighting="none"' },
      { symbol: 'w_k', meaning: "The one client's locally-trained weights being folded in this step" },
    ],
    workflow: [
      'A pool of `async_concurrency` clients trains concurrently against whatever the global model is when they start.',
      'A discrete-event simulation (heapq, keyed by simulated finish time from each client\'s speed) determines the arrival order.',
      'When a client finishes, its staleness s = t − τ is computed against the current global version t.',
      'Its update is mixed into the global model with weight α_eff = α · f(s) — the more stale, the smaller the step.',
      'The now-freed client slot is immediately redispatched against the (just-updated) global model.',
      'This repeats one client-update at a time until the configured number of updates is reached; metrics are logged every `async_updates_per_log` updates.',
    ],
  },
  {
    id: 'fedfa',
    label: 'FedFA',
    type: 'asynchronous',
    color: 'emerald',
    intuition:
      "FedFA is a middle ground between FedAvg's synchronous batch-averaging and FedAsync's one-at-a-time mixing. " +
      "It keeps a small rolling buffer of the most recent client updates. Whenever a new client finishes, it's " +
      "merged together with everything currently sitting in the buffer in one batched, staleness-weighted average — " +
      "so the global model benefits from several clients' worth of signal per update (smoother than FedAsync's " +
      "single-client mixing) while still not blocking on the slowest client (unlike FedAvg).",
    formulas: [
      { label: 'Local training (client k, dispatched at global version τ_k)', expr: 'w_k = LocalSGD(w_τ_k, D_k)' },
      { label: 'Staleness weight per contributing update i (buffered or fresh)', expr: 'w_i = f(t − τ_i),  f(s) = 1/(1+s)  ("inverse") or 1 ("none")' },
      { label: 'Batched weighted merge over the buffer ∪ current update', expr: 'w_(t+1) = Σ_i  ( w_i / Σ_j w_j ) · state_i' },
    ],
    variables: [
      { symbol: 'B', meaning: 'Buffer capacity (fedfa_buffer_size) — the deque holding the most recent finished updates' },
      { symbol: 'τ_i', meaning: 'Global version that contributing update i was dispatched from' },
      { symbol: 't', meaning: 'Current global version at merge time' },
      { symbol: 'w_i', meaning: 'Staleness-based weight assigned to update i in this merge (recomputed fresh every merge, since staleness keeps growing while an entry waits in the buffer)' },
      { symbol: 'state_i', meaning: "Update i's model weights (either freshly arrived, or still sitting in the buffer from a previous step)" },
    ],
    workflow: [
      'A pool of clients trains concurrently, exactly as in FedAsync (same discrete-event dispatch/finish simulation).',
      'When a client finishes, its state is combined with every state currently in the fixed-size buffer.',
      "Each contributing state's weight is recomputed from its own staleness relative to the current global version.",
      'All contributing states are merged in one shot: a weighted average normalized by the sum of weights.',
      'The freshly-finished update is then pushed into the buffer (evicting the oldest entry once the buffer is full), and the client slot is redispatched.',
      'Metrics are logged every `async_updates_per_log` updates, same cadence as FedAsync.',
    ],
  },
];

const COLOR_MAP: Record<AlgoDoc['color'], { text: string; bg: string; border: string; dot: string }> = {
  cyan:    { text: 'text-cyan-400',    bg: 'bg-cyan-500/10',    border: 'border-cyan-500/20',    dot: 'bg-cyan-400'    },
  emerald: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', dot: 'bg-emerald-400' },
  amber:   { text: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/20',   dot: 'bg-amber-400'   },
  purple:  { text: 'text-purple-400',  bg: 'bg-purple-500/10',  border: 'border-purple-500/20',  dot: 'bg-purple-400'  },
};

export default function Algorithms() {
  const [activeId, setActiveId] = useState(ALGO_DOCS[0].id);
  const active = ALGO_DOCS.find(a => a.id === activeId)!;
  const c = COLOR_MAP[active.color];

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <BookOpen size={20} className="text-cyan-400" />
          Algorithm Reference
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Intuition, mathematics, and workflow for every FL algorithm supported by this platform.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Algorithm selector */}
        <div className="card-glow lg:col-span-1 h-fit">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Layers size={14} /> Algorithms
          </h2>
          <div className="space-y-2">
            {ALGO_DOCS.map(algo => {
              const ac = COLOR_MAP[algo.color];
              const isActive = algo.id === activeId;
              return (
                <button
                  key={algo.id}
                  onClick={() => setActiveId(algo.id)}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg border transition-all flex items-center justify-between group',
                    isActive
                      ? clsx(ac.bg, ac.border)
                      : 'bg-[#1e293b] border-transparent hover:border-[#334155]',
                  )}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={clsx('w-1.5 h-1.5 rounded-full', ac.dot)} />
                      <span className={clsx('text-sm font-semibold', isActive ? ac.text : 'text-slate-200')}>
                        {algo.label}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 mt-0.5 block">
                      {algo.type === 'synchronous' ? 'Synchronous' : 'Asynchronous'}
                    </span>
                  </div>
                  <ChevronRight
                    size={14}
                    className={clsx(
                      'flex-shrink-0 transition-transform',
                      isActive ? clsx(ac.text, 'translate-x-0.5') : 'text-slate-600',
                    )}
                  />
                </button>
              );
            })}
          </div>
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-3 space-y-5">
          {/* Title + Description */}
          <div className={clsx('card border', c.bg, c.border)}>
            <div className="flex items-center gap-2">
              <h2 className={clsx('text-lg font-bold', c.text)}>{active.label}</h2>
              <span
                className={clsx(
                  'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border',
                  c.bg,
                  c.border,
                  c.text,
                )}
              >
                {active.type}
              </span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed mt-4">
              {active.intuition}
            </p>
          </div>

          {/* Formulas */}
          <div className="card-glow">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Sigma size={15} className={c.text} /> Mathematical Formulation
            </h3>
            <div className="space-y-2.5">
              {active.formulas.map(({ label, expr }, i) => (
                <div key={i} className="bg-[#0a0f1e] border border-[#1e293b] rounded-lg px-4 py-3">
                  <p className="text-[11px] text-slate-500 mb-1">{label}</p>
                  <p className="font-mono text-sm text-slate-100 overflow-x-auto whitespace-nowrap">{expr}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Variable definitions */}
          <div className="card-glow">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Network size={15} className={c.text} /> Variable Definitions
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {active.variables.map(({ symbol, meaning }, i) => (
                <div key={i} className="flex gap-3 bg-[#1e293b]/50 rounded-lg px-3 py-2.5">
                  <span className={clsx('font-mono text-sm font-semibold flex-shrink-0', c.text)}>{symbol}</span>
                  <span className="text-xs text-slate-400 leading-relaxed">{meaning}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Workflow */}
          <div className="card-glow">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <ListOrdered size={15} className={c.text} /> Logical Workflow
            </h3>
            <ol className="space-y-2.5">
              {active.workflow.map((step, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                  <span className={clsx(
                    'flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono mt-0.5',
                    c.bg, c.text, 'border', c.border,
                  )}>
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          {/* Compatibility footer */}
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <GitMerge size={13} />
            {active.type === 'synchronous' ? (
              <span>Compatible with Secure Aggregation and Differential Privacy.</span>
            ) : active.id === 'fedfa' ? (
              <span>Compatible with Secure Aggregation (buffered batch) and Differential Privacy.</span>
            ) : (
              <span>Differential Privacy applies per update; Secure Aggregation is not applicable (single-update async merge has nothing to mask against).</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
