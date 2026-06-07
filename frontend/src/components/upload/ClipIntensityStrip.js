import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ScanLine, AlertCircle } from 'lucide-react';

/**
 * ClipIntensityStrip
 * ------------------
 * Calls /api/video/analyze for the session and renders a per-clip strip:
 *   - filename, duration
 *   - 1-10 intensity score (color-coded)
 *   - mini sparkline of action/calm segments
 *
 * Lightweight + best-effort: if scene analysis is unavailable (e.g. PyAV
 * missing in the runtime) we silently render nothing.
 */
const ClipIntensityStrip = ({ sessionId, backendUrl, className = '' }) => {
  const [clips, setClips] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sessionId || !backendUrl) return;
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await fetch(`${backendUrl}/api/video/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
        const body = await resp.json();
        if (!resp.ok) throw new Error(body?.detail || `HTTP ${resp.status}`);
        if (!cancelled) setClips(body.clips || []);
      } catch (err) {
        if (!cancelled) setError(err.message || String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [sessionId, backendUrl]);

  // Silently bail when analysis is unsupported (e.g. PyAV missing)
  if (!sessionId) return null;
  if (error && /pyav|unavailable|503/i.test(error)) return null;

  const scoreColor = (s) => {
    if (s >= 8) return 'from-pink-500 to-rose-400 text-pink-100 border-pink-400/60';
    if (s >= 5) return 'from-violet-500 to-purple-400 text-violet-100 border-violet-400/60';
    if (s >= 3) return 'from-cyan-500 to-blue-400 text-cyan-100 border-cyan-400/60';
    return 'from-gray-700 to-gray-600 text-gray-200 border-white/10';
  };

  return (
    <motion.div
      data-testid="clip-intensity-strip"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`glass-effect rounded-2xl p-5 border border-cyan-400/20 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-cyan-300">
          <ScanLine className="w-4 h-4" />
          <span className="text-sm font-semibold uppercase tracking-wider">
            Clip Intensity
          </span>
        </div>
        {loading && (
          <span className="text-xs text-cyan-300 font-mono animate-pulse">
            scanning…
          </span>
        )}
      </div>

      {!loading && error && (
        <div className="flex items-center gap-2 text-amber-300 text-xs px-2">
          <AlertCircle className="w-4 h-4" />
          <span>Clip analysis unavailable: {error}</span>
        </div>
      )}

      {!loading && !error && clips && clips.length === 0 && (
        <p className="text-xs text-gray-500">No clips to analyse.</p>
      )}

      {!loading && !error && clips && clips.length > 0 && (
        <ul className="space-y-2">
          {clips.map((c, i) => {
            const score = Math.round(c.score_1_to_10 || 0);
            const name = (c.clip_path || '').split('/').pop() || `clip-${i + 1}`;
            const cuts = (c.scene_cuts || []).length;
            return (
              <li
                key={c.clip_path}
                data-testid={`clip-row-${i}`}
                className="flex items-center gap-3 rounded-lg bg-white/[0.02] border border-white/5 px-3 py-2"
              >
                <div
                  className={`shrink-0 h-9 w-9 rounded-md grid place-items-center font-mono font-bold text-sm bg-gradient-to-br border ${scoreColor(
                    score,
                  )}`}
                  data-testid={`clip-score-${i}`}
                  title="Intensity score 1-10"
                >
                  {score || '—'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white truncate">{name}</div>
                  <div className="text-[11px] text-gray-400 font-mono">
                    {c.duration ? `${c.duration.toFixed(1)}s` : '—'} ·{' '}
                    motion {Math.round(c.motion_score || 0)} · {cuts} cuts
                  </div>
                </div>
                {/* tiny action-segment bar */}
                <div className="hidden sm:block w-32 h-2 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-400 via-violet-400 to-pink-400"
                    style={{ width: `${Math.min(100, score * 10)}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </motion.div>
  );
};

export default ClipIntensityStrip;
