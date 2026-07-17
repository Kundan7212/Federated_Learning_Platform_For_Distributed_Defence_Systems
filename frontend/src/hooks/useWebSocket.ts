import { useEffect, useRef, useState, useCallback } from 'react';
import { getWsUrl } from '../api/client';
import type { WsMessage, WsRoundUpdate, ExperimentStatus } from '../types';

export interface LiveMetric {
  round:    number;
  accuracy: number;
  loss:     number;
  epsilon?: number;
}

interface WsState {
  connected:    boolean;
  status:       ExperimentStatus | null;
  metrics:      LiveMetric[];
  progressPct:  number;
  finalResult:  WsMessage | null;
  error:        string | null;
  budgetUsedPct: number | null;
  privacyAlert:  string | null;
}

export function useTrainingWebSocket(experimentId: string | null) {
  const wsRef     = useRef<WebSocket | null>(null);
  const pingRef   = useRef<ReturnType<typeof setInterval> | null>(null);

  const [state, setState] = useState<WsState>({
    connected:   false,
    status:      null,
    metrics:     [],
    progressPct: 0,
    finalResult: null,
    error:       null,
    budgetUsedPct: null,
    privacyAlert:  null,
  });

  const disconnect = useCallback(() => {
    if (pingRef.current) clearInterval(pingRef.current);
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent reconnect loop
      wsRef.current.close();
      wsRef.current = null;
    }
    setState(s => ({ ...s, connected: false }));
  }, []);

  useEffect(() => {
    if (!experimentId) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    const url = getWsUrl(experimentId);
    const ws  = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
      setState(s => ({ ...s, connected: true, error: null }));

      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 25000);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (event.data === '{"type":"pong"}') return;

      try {
        const msg = JSON.parse(event.data) as WsMessage;

        switch (msg.type) {
          case 'round_update': {
            const p = (msg as WsRoundUpdate).payload;
            setState(s => ({
              ...s,
              status:      'running',
              progressPct: p.progress_pct,
              budgetUsedPct: p.budget_used_pct ?? s.budgetUsedPct,
              metrics: [
                ...s.metrics,
                { round: p.round_num, accuracy: p.accuracy, loss: p.loss, epsilon: p.epsilon },
              ],
            }));
            break;
          }
          case 'privacy_alert': {
            const p = msg.payload;
            setState(s => ({ ...s, budgetUsedPct: p.budget_used_pct, privacyAlert: p.message }));
            break;
          }
          case 'status_change':
            setState(s => ({ ...s, status: msg.payload.status }));
            break;
          case 'complete':
            setState(s => ({
              ...s,
              status:      'completed',
              progressPct: 100,
              finalResult: msg,
            }));
            break;
          case 'error':
            setState(s => ({
              ...s,
              error: msg.payload.error,
            }));
            break;
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      setState(s => ({ ...s, error: 'WebSocket connection error', connected: false }));
    };

    ws.onclose = () => {
      if (pingRef.current) clearInterval(pingRef.current);
      setState(s => ({ ...s, connected: false }));
    };

    return () => { disconnect(); };
  }, [experimentId, disconnect]);

  return { ...state, disconnect };
}
