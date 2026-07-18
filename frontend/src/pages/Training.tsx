import { useState, useEffect } from 'react';
import {
  Play, Square, ChevronDown, ChevronUp,
  Shield, Zap, Settings, CheckCircle2, AlertCircle, Wifi, WifiOff
} from 'lucide-react';
import { experimentsApi, trainingApi, metricsApi } from '../api/client';
import { AccuracyChart, LossChart, EpsilonChart } from '../components/MetricsChart';
import { ProgressBar, StatusBadge } from '../components/StatCard';
import { useTrainingWebSocket } from '../hooks/useWebSocket';
import type { AlgorithmMeta, CreateExperimentRequest } from '../types';

const DEFAULT_CFG: CreateExperimentRequest = {
  name: '',
  description: '',
  fl_config: {
    algorithm: 'fedavg', dataset: 'mnist', model_type: 'cnn',
    num_clients: 10, rounds: 5, local_epochs: 2,
    batch_size: 32, learning_rate: 0.01, partition_method: 'dirichlet',
    dirichlet_alpha: 0.5, async_alpha: 0.1, async_concurrency: 3,
    async_updates_per_log: 10, fedfa_buffer_size: 4, fedprox_mu: 0.01,
    staleness_weighting: 'inverse', client_speed_profile: 'uniform',
  },
  privacy: {
    dp_enabled: false, noise_multiplier: 1.0, max_grad_norm: 1.0, sa_enabled: false,
  },
};

function FormRow({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-600 mt-1">{hint}</p>}
    </div>
  );
}

export default function Training() {
  const [cfg, setCfg]               = useState<CreateExperimentRequest>(DEFAULT_CFG);
  const [algos, setAlgos]           = useState<AlgorithmMeta[]>([]);
  const [showAdvanced, setShowAdv]  = useState(false);
  const [phase, setPhase]           = useState<'form' | 'training' | 'done'>('form');
  const [experimentId, setExpId]    = useState<string | null>(null);
  const [totalRounds, setTotalRounds] = useState(5);
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const ws = useTrainingWebSocket(phase === 'training' ? experimentId : null);

  useEffect(() => {
    metricsApi.algorithms().then(r => setAlgos(r.data));
  }, []);

  useEffect(() => {
    if (ws.status === 'completed' || ws.status === 'failed' || ws.status === 'cancelled') {
      setPhase('done');
    }
  }, [ws.status]);

  function setFL(key: string, val: unknown) {
    setCfg(c => ({ ...c, fl_config: { ...c.fl_config, [key]: val } }));
  }
  function setPriv(key: string, val: unknown) {
    setCfg(c => ({ ...c, privacy: { ...c.privacy, [key]: val } }));
  }

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    if (!cfg.name.trim()) { setSubmitError('Experiment name is required'); return; }
    setSubmitError('');
    setSubmitting(true);
    try {
      const { data: exp } = await experimentsApi.create(cfg);
      await trainingApi.start(exp.id);
      setExpId(exp.id);
      setTotalRounds(cfg.fl_config.rounds);
      setPhase('training');
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    if (experimentId && !cancelling) {
      setCancelling(true);
      try {
        await trainingApi.cancel(experimentId);
      } catch (err: any) {
        // 409 means it's already cancelled/finished server-side — treat as
        // success so the UI doesn't leave a clickable button around forever.
        if (err?.response?.status !== 409) {
          setCancelling(false);
          return;
        }
      }
      // Don't wait on the WebSocket status_change message to arrive —
      // reflect the cancellation locally right away.
      setPhase('done');
    }
  }

  const isAsync = ['fedasync', 'fedfa'].includes(cfg.fl_config.algorithm);
  const algoMeta = algos.find(a => a.value === cfg.fl_config.algorithm);
  const secureAggCompatible = algoMeta ? algoMeta.secure_agg_compatible : cfg.fl_config.algorithm !== 'fedasync';

  useEffect(() => {
    if (!secureAggCompatible && cfg.privacy.sa_enabled) {
      setPriv('sa_enabled', false);
    }
  }, [secureAggCompatible]);

  if (phase === 'training' || phase === 'done') {
    return (
      <div className="p-6 space-y-5 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-100">
              {cfg.name || 'Federated Training'}
            </h1>
            <p className="text-xs font-mono text-slate-500 mt-0.5">
              {cfg.fl_config.algorithm.toUpperCase()} · {cfg.fl_config.dataset.toUpperCase()} · {cfg.fl_config.num_clients} clients
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* WS connection status */}
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              {ws.connected ? (
                <><Wifi size={12} className="text-emerald-400" /> LIVE</>
              ) : (
                <><WifiOff size={12} className="text-slate-600" /> OFFLINE</>
              )}
            </span>
            {phase === 'training' && ws.status !== 'completed' && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="btn-danger flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Square size={14} /> {cancelling ? 'Cancelling…' : 'Cancel'}
              </button>
            )}
            {phase === 'done' && (
              <button onClick={() => { setPhase('form'); setCfg(DEFAULT_CFG); }} className="btn-secondary text-sm">
                New Experiment
              </button>
            )}
          </div>
        </div>

        {/* Progress */}
        <div className="card-glow">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {ws.status === 'running' || phase === 'training' ? (
                <StatusBadge status="running" />
              ) : ws.status === 'completed' ? (
                <StatusBadge status="completed" />
              ) : ws.status === 'failed' ? (
                <StatusBadge status="failed" />
              ) : (
                <StatusBadge status="pending" />
              )}
              <span className="text-xs text-slate-500 font-mono">
                Round {ws.metrics.length} / {totalRounds}
              </span>
            </div>
            {ws.status === 'completed' && (
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle2 size={16} />
                <span className="text-sm font-semibold">Training Complete</span>
              </div>
            )}
            {ws.error && (
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle size={16} />
                <span className="text-sm">{ws.error}</span>
              </div>
            )}
          </div>
          <ProgressBar value={ws.progressPct} label="Training Progress" />
        </div>

        {/* Privacy budget monitoring */}
        {cfg.privacy.dp_enabled && ws.budgetUsedPct != null && (
          <div className={`card-glow ${ws.budgetUsedPct >= 100 ? 'border-red-500/30' : ws.budgetUsedPct >= 80 ? 'border-amber-500/30' : ''}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <Shield size={13} /> Privacy Budget
              </span>
              {ws.privacyAlert && (
                <span className="flex items-center gap-1.5 text-amber-400 text-xs">
                  <AlertCircle size={12} /> {ws.privacyAlert}
                </span>
              )}
            </div>
            <ProgressBar value={Math.min(ws.budgetUsedPct, 100)} label={`ε Budget Used — ${ws.budgetUsedPct.toFixed(1)}%`} />
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AccuracyChart metrics={ws.metrics} totalRounds={totalRounds} />
          <LossChart     metrics={ws.metrics} totalRounds={totalRounds} />
        </div>

        {cfg.privacy.dp_enabled && (
          <EpsilonChart metrics={ws.metrics} />
        )}

        {/* Final summary */}
        {phase === 'done' && ws.metrics.length > 0 && (
          <div className="card-glow border-emerald-500/20">
            <h3 className="text-sm font-semibold text-emerald-400 mb-4">Training Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              {[
                { label: 'Final Accuracy', value: `${ws.metrics[ws.metrics.length-1].accuracy.toFixed(2)}%`, color: 'text-emerald-400' },
                { label: 'Best Accuracy',  value: `${Math.max(...ws.metrics.map(m=>m.accuracy)).toFixed(2)}%`, color: 'text-cyan-400' },
                { label: 'Final Loss',     value: ws.metrics[ws.metrics.length-1].loss.toFixed(4), color: 'text-amber-400' },
                { label: 'Total Rounds',   value: ws.metrics.length, color: 'text-slate-300' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-[#1e293b] rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">{label}</p>
                  <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-6 animate-fade-in">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-100">New Training Experiment</h1>
          <p className="text-sm text-slate-500 mt-0.5">Configure and launch a federated learning run.</p>
        </div>

        <form onSubmit={handleStart} className="space-y-5">
          {/* Basic Info */}
          <div className="card-glow space-y-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Settings size={14} /> Experiment Details
            </h2>
            <FormRow label="Experiment Name">
              <input
                className="input" required placeholder="e.g. FedAvg MNIST Baseline"
                value={cfg.name} onChange={e => setCfg(c => ({ ...c, name: e.target.value }))}
              />
            </FormRow>
            <FormRow label="Description (optional)">
              <textarea
                className="input resize-none h-20" placeholder="Brief description…"
                value={cfg.description}
                onChange={e => setCfg(c => ({ ...c, description: e.target.value }))}
              />
            </FormRow>
          </div>

          {/* FL Config */}
          <div className="card-glow space-y-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Zap size={14} /> Federated Learning Configuration
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormRow label="Algorithm">
                <select className="input" value={cfg.fl_config.algorithm}
                  onChange={e => setFL('algorithm', e.target.value)}>
                  {algos.length ? algos.map(a => (
                    <option key={a.value} value={a.value}>{a.label} — {a.type}</option>
                  )) : (
                    <>
                      <option value="fedavg">FedAvg — Synchronous</option>
                      <option value="fedasync">FedAsync — Asynchronous</option>
                      <option value="fedfa">FedFA — Async + Buffer</option>
                      <option value="fedprox">FedProx — Proximal</option>
                    </>
                  )}
                </select>
                {algos.find(a => a.value === cfg.fl_config.algorithm) && (
                  <p className="text-xs text-slate-600 mt-1">
                    {algos.find(a => a.value === cfg.fl_config.algorithm)?.description}
                  </p>
                )}
              </FormRow>

              <FormRow label="Dataset">
                <select className="input" value={cfg.fl_config.dataset}
                  onChange={e => setFL('dataset', e.target.value)}>
                  <option value="mnist">MNIST (10 classes, fast)</option>
                  <option value="emnist">EMNIST (47 classes, ~400MB)</option>
                </select>
              </FormRow>

              <FormRow label="Model Architecture">
                <select className="input" value={cfg.fl_config.model_type}
                  onChange={e => setFL('model_type', e.target.value)}>
                  <option value="cnn">CNN (2-layer ConvNet)</option>
                  <option value="mlp">MLP (2-layer Perceptron)</option>
                </select>
              </FormRow>

              <FormRow label="Data Partition">
                <select className="input" value={cfg.fl_config.partition_method}
                  onChange={e => setFL('partition_method', e.target.value)}>
                  <option value="iid">IID — Equal random split</option>
                  <option value="dirichlet">Dirichlet — Non-IID realistic</option>
                  <option value="label_skew">Label Skew — 2 shards per client</option>
                </select>
              </FormRow>

              <FormRow label="Number of Clients" hint="Federated participants">
                <input type="number" className="input" min={2} max={100}
                  value={cfg.fl_config.num_clients}
                  onChange={e => setFL('num_clients', +e.target.value)} />
              </FormRow>

              <FormRow label="Training Rounds" hint="Global aggregation rounds">
                <input type="number" className="input" min={1} max={100}
                  value={cfg.fl_config.rounds}
                  onChange={e => setFL('rounds', +e.target.value)} />
              </FormRow>

              <FormRow label="Local Epochs" hint="SGD epochs per round per client">
                <input type="number" className="input" min={1} max={20}
                  value={cfg.fl_config.local_epochs}
                  onChange={e => setFL('local_epochs', +e.target.value)} />
              </FormRow>

              <FormRow label="Batch Size">
                <input type="number" className="input" min={8} max={256}
                  value={cfg.fl_config.batch_size}
                  onChange={e => setFL('batch_size', +e.target.value)} />
              </FormRow>

              <FormRow label="Learning Rate">
                <input type="number" className="input" step={0.01} min={0.01} max={1}
                  value={cfg.fl_config.learning_rate}
                  onChange={e => setFL('learning_rate', parseFloat(e.target.value))} />
              </FormRow>

              {cfg.fl_config.partition_method === 'dirichlet' && (
                <FormRow label="Dirichlet α" hint="Lower = more non-IID">
                  <input type="number" className="input" step={0.01} min={0.01} max={10}
                    value={cfg.fl_config.dirichlet_alpha}
                    onChange={e => setFL('dirichlet_alpha', parseFloat(e.target.value))} />
                </FormRow>
              )}

              {cfg.fl_config.algorithm === 'fedprox' && (
                <FormRow label="FedProx μ" hint="Proximal term coefficient">
                  <input type="number" className="input" step={0.001} min={0} max={1}
                    value={cfg.fl_config.fedprox_mu}
                    onChange={e => setFL('fedprox_mu', parseFloat(e.target.value))} />
                </FormRow>
              )}
            </div>

            {/* Advanced async settings */}
            {isAsync && (
              <div>
                <button type="button"
                  onClick={() => setShowAdv(v => !v)}
                  className="text-xs text-cyan-400 flex items-center gap-1 hover:text-cyan-300 transition-colors"
                >
                  {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  Async Settings
                </button>
                {showAdvanced && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 pt-3 border-t border-[#1e293b]">
                    <FormRow label="Async α" hint="Update mixing coefficient">
                      <input type="number" className="input" step={0.01} min={0.01} max={1}
                        value={cfg.fl_config.async_alpha}
                        onChange={e => setFL('async_alpha', parseFloat(e.target.value))} />
                    </FormRow>
                    <FormRow label="Concurrency" hint="Parallel clients in flight">
                      <input type="number" className="input" min={1} max={20}
                        value={cfg.fl_config.async_concurrency}
                        onChange={e => setFL('async_concurrency', +e.target.value)} />
                    </FormRow>
                    <FormRow label="Updates per Log" hint="Rounds = updates ÷ this">
                      <input type="number" className="input" min={1} max={100}
                        value={cfg.fl_config.async_updates_per_log}
                        onChange={e => setFL('async_updates_per_log', +e.target.value)} />
                    </FormRow>
                    <FormRow label="Client Speed Profile" hint="Per-client relative speed heterogeneity">
                      <select className="input" value={cfg.fl_config.client_speed_profile}
                        onChange={e => setFL('client_speed_profile', e.target.value)}>
                        <option value="uniform">Uniform</option>
                        <option value="mild">Mild Heterogeneity</option>
                        <option value="high">High Heterogeneity</option>
                      </select>
                    </FormRow>
                    {cfg.fl_config.algorithm === 'fedfa' && (
                      <FormRow label="FedFA Buffer Size">
                        <input type="number" className="input" min={1} max={20}
                          value={cfg.fl_config.fedfa_buffer_size}
                          onChange={e => setFL('fedfa_buffer_size', +e.target.value)} />
                      </FormRow>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Privacy */}
          <div className="card-glow space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <Shield size={14} /> Privacy Configuration
              </h2>
            </div>

            <div className="flex items-center gap-3">
              <button type="button"
                onClick={() => setPriv('dp_enabled', !cfg.privacy.dp_enabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${cfg.privacy.dp_enabled ? 'bg-cyan-600' : 'bg-[#334155]'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${cfg.privacy.dp_enabled ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
              <span className="text-sm text-slate-300">Differential Privacy (ε,δ)</span>
              {cfg.privacy.dp_enabled && (
                <span className="badge-running text-xs">ACTIVE</span>
              )}
            </div>

            {cfg.privacy.dp_enabled && (
              <div className="grid grid-cols-2 gap-4 pl-4 border-l border-cyan-500/20">
                <FormRow label="Noise Multiplier σ" hint="Higher = more private, less accurate">
                  <input type="number" className="input" step={0.1} min={0.1} max={100}
                    value={cfg.privacy.noise_multiplier}
                    onChange={e => setPriv('noise_multiplier', parseFloat(e.target.value))} />
                </FormRow>
                <FormRow label="Max Gradient Norm C" hint="L2 clipping bound">
                  <input type="number" className="input" step={0.1} min={0.1} max={100}
                    value={cfg.privacy.max_grad_norm}
                    onChange={e => setPriv('max_grad_norm', parseFloat(e.target.value))} />
                </FormRow>
              </div>
            )}

            <div className="flex items-center gap-3">
              <button type="button"
                disabled={!secureAggCompatible}
                onClick={() => setPriv('sa_enabled', !cfg.privacy.sa_enabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  !secureAggCompatible ? 'bg-[#1e293b] cursor-not-allowed opacity-50' :
                  cfg.privacy.sa_enabled ? 'bg-purple-600' : 'bg-[#334155]'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${cfg.privacy.sa_enabled && secureAggCompatible ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
              <span className={`text-sm ${secureAggCompatible ? 'text-slate-300' : 'text-slate-600'}`}>Secure Aggregation (Additive Masking)</span>
            </div>
            {!secureAggCompatible && (
              <p className="text-xs text-slate-600 -mt-2">
                Not available for {cfg.fl_config.algorithm.toUpperCase()} — each update is applied to the global model alone, so masks have no partner to cancel against.
              </p>
            )}
          </div>

          {submitError && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm">
              {submitError}
            </div>
          )}

          <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2"
            disabled={submitting}>
            {submitting ? (
              <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> INITIALISING...</>
            ) : (
              <><Play size={16} /> LAUNCH EXPERIMENT</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
