export interface TokenResponse {
  access_token: string;
  token_type:   string;
  expires_in:   number;
  user_id:      string;
  username:     string;
  email:        string;
}

export interface User {
  id:        string;
  email:     string;
  username:  string;
  is_active: boolean;
  is_admin:  boolean;
}

export interface FLConfig {
  algorithm:           string;
  dataset:             string;
  model_type:          string;
  num_clients:         number;
  rounds:              number;
  local_epochs:        number;
  batch_size:          number;
  learning_rate:       number;
  partition_method:    string;
  dirichlet_alpha:     number;
  async_alpha:         number;
  async_concurrency:   number;
  async_updates_per_log: number;
  fedfa_buffer_size:   number;
  fedprox_mu:          number;
  staleness_weighting: string;
  client_speed_profile: string;
}

export interface PrivacyOptions {
  dp_enabled:       boolean;
  noise_multiplier: number;
  max_grad_norm:    number;
  sa_enabled:       boolean;
}

export interface CreateExperimentRequest {
  name:        string;
  description: string;
  fl_config:   FLConfig;
  privacy:     PrivacyOptions;
}

export type ExperimentStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Experiment {
  id:               string;
  name:             string;
  description:      string | null;
  algorithm:        string;
  dataset:          string;
  model_type:       string;
  num_clients:      number;
  rounds:           number;
  local_epochs:     number;
  batch_size:       number;
  learning_rate:    number;
  partition_method: string;
  dp_enabled:       boolean;
  sa_enabled:       boolean;
  noise_mult:       number | null;
  max_grad_norm:    number | null;
  status:           ExperimentStatus;
  final_accuracy:   number | null;
  best_accuracy:    number | null;
  final_loss:       number | null;
  total_epsilon:    number | null;
  error_message:    string | null;
  owner_id:         string;
  created_at:       string;
  started_at:       string | null;
  finished_at:      string | null;
  duration_seconds: number | null;
}

export interface RoundMetric {
  round_num:   number;
  accuracy:    number;
  loss:        number;
  extra:       Record<string, unknown> | null;
  recorded_at: string;
}

export interface PrivacyLog {
  round_num:     number;
  epsilon_round: number;
  epsilon_total: number;
  delta:         number;
  noise_mult:    number;
  clip_norm:     number;
  recorded_at:   string;
}

export interface ExperimentDetail extends Experiment {
  round_metrics: RoundMetric[];
  privacy_logs:  PrivacyLog[];
}

export interface TrainingStatus {
  experiment_id:   string;
  status:          ExperimentStatus;
  current_round:   number;
  total_rounds:    number;
  latest_accuracy: number | null;
  latest_loss:     number | null;
  total_epsilon:   number | null;
  progress_pct:    number;
}

export interface WsRoundUpdate {
  type: 'round_update';
  payload: {
    experiment_id: string;
    round_num:     number;
    total_rounds:  number;
    accuracy:      number;   
    loss:          number;
    progress_pct:  number;
    epsilon?:      number;
    budget_used_pct?: number | null;
    algorithm?:    string;
    staleness?:    number;
  };
}

export interface WsStatusChange {
  type: 'status_change';
  payload: { status: ExperimentStatus; experiment_id: string };
}

export interface WsComplete {
  type: 'complete';
  payload: {
    experiment_id:  string;
    status:         string;
    final_accuracy: number;
    best_accuracy:  number;
    final_loss:     number;
    total_epsilon:  number | null;
  };
}

export interface WsError {
  type: 'error';
  payload: { experiment_id: string; error: string };
}

export interface WsPrivacyAlert {
  type: 'privacy_alert';
  payload: {
    experiment_id:    string;
    budget_used_pct:  number;
    message:          string;
  };
}

export type WsMessage = WsRoundUpdate | WsStatusChange | WsComplete | WsError | WsPrivacyAlert;

export interface DashboardStats {
  total_experiments: number;
  running_count:     number;
  completed_count:   number;
  best_accuracy:     number;
  avg_accuracy:      number;
  dp_experiments:    number;
  total_rounds:      number;
  recent_experiments: {
    id:             string;
    name:           string;
    algorithm:      string;
    status:         ExperimentStatus;
    final_accuracy: number | null;
    created_at:     string;
  }[];
}

export interface AlgorithmMeta {
  value:       string;
  label:       string;
  description: string;
  type:        string;
  paper:       string;
  secure_agg_compatible: boolean;
}
