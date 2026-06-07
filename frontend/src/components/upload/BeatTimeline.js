import React, { useEffect, useState, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { Music2, Activity, AlertCircle } from 'lucide-react';

/**
 * BeatTimeline
 * -----------
 * Visualises a track's beat grid + energy envelope.
 * Fetches /api/audio/beats once a session has an audio file uploaded.
 *
 * Props:
 *   sessionId        : string | null - upload session containing the audio
 *   backendUrl       : string         - resolved REACT_APP_BACKEND_URL
 *   className        : string         - optional extra classes
 *
 * Visuals:
 *   - top-line  : energy ribbon (gradient cyan -> magenta, height drives by
 *                 normalised energy)
 *   - bar lines : every beat from the synthesized beat grid
 *   - drops     : larger magenta bars on detected drops
 */
const BeatTimeline = ({ sessionId, backendUrl, className = '' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);
  const [width, setWidth] = useState(800);

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(Math.max(280, entry.contentRect.width));
      }
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!sessionId || !backendUrl) return;
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await fetch(`${backendUrl}/api/audio/beats`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
        const body = await resp.json();
        if (!resp.ok) throw new Error(body?.detail || `HTTP ${resp.status}`);
        if (!cancelled) setData(body);
      } catch (err) {
        if (!cancelled) setError(err.message || String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [sessionId, backendUrl]);

  const { svgPaths, beatXs, dropXs, duration, bpm } = useMemo(() => {
    if (!data) return { svgPaths: '', beatXs: [], dropXs: [], duration: 0, bpm: 0 };
    const dur = Math.max(0.001, data.duration_seconds || 1);
    const energy = data.energy_curve || [];
    const grid = data.beat_grid || [];
    const drops = data.drops || [];
    const W = width;
    const H = 80;
    const PAD_X = 8;
    const innerW = W - PAD_X * 2;

    // Energy ribbon path (smoothed area)
    let path = '';
    if (energy.length) {
      const maxE = Math.max(...energy, 0.0001);
      const step = innerW / Math.max(1, energy.length - 1);
      const pts = energy.map((e, i) => {
        const x = PAD_X + i * step;
        const y = H - 6 - ((e / maxE) * (H - 14));
        return [x, y];
      });
      path = `M ${PAD_X} ${H - 6} `;
      pts.forEach(([x, y]) => { path += `L ${x.toFixed(1)} ${y.toFixed(1)} `; });
      path += `L ${W - PAD_X} ${H - 6} Z`;
    }

    const beatXsList = grid.map((t) => PAD_X + (t / dur) * innerW);
    const dropXsList = drops.map((t) => PAD_X + (t / dur) * innerW);

    return {
      svgPaths: path,
      beatXs: beatXsList,
      dropXs: dropXsList,
      duration: dur,
      bpm: data.bpm || 0,
    };
  }, [data, width]);

  if (!sessionId) return null;

  return (
    <motion.div
      data-testid="beat-timeline"
      ref={containerRef}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`glass-effect rounded-2xl p-5 border border-cyan-400/20 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-cyan-300">
          <Activity className="w-4 h-4" />
          <span className="text-sm font-semibold uppercase tracking-wider">
            Beat &amp; Energy Map
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-400 font-mono">
          {bpm > 0 && (
            <span data-testid="beat-bpm" className="text-pink-300">
              {Math.round(bpm)} BPM
            </span>
          )}
          {duration > 0 && (
            <span data-testid="beat-duration">{duration.toFixed(1)}s</span>
          )}
          {data?.beat_count != null && (
            <span data-testid="beat-count">{data.beat_count} beats</span>
          )}
          {data?.drop_count != null && data.drop_count > 0 && (
            <span data-testid="beat-drops" className="text-pink-400">
              {data.drop_count} drops
            </span>
          )}
        </div>
      </div>

      <div className="relative rounded-lg overflow-hidden bg-cyber-dark/60 border border-white/5">
        {loading && (
          <div className="flex items-center justify-center h-20 text-cyan-300 text-sm">
            <Music2 className="w-4 h-4 mr-2 animate-pulse" />
            Analysing beats…
          </div>
        )}
        {!loading && error && (
          <div className="flex items-center justify-center gap-2 h-20 text-amber-300 text-sm px-4 text-center">
            <AlertCircle className="w-4 h-4" />
            <span>Beat analysis unavailable: {error}</span>
          </div>
        )}
        {!loading && !error && data && (
          <svg
            width="100%"
            height="80"
            viewBox={`0 0 ${width} 80`}
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="bt-energy" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.85" />
                <stop offset="55%" stopColor="#a855f7" stopOpacity="0.55" />
                <stop offset="100%" stopColor="#ec4899" stopOpacity="0.15" />
              </linearGradient>
              <linearGradient id="bt-grid" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#67e8f9" stopOpacity="0.65" />
                <stop offset="100%" stopColor="#67e8f9" stopOpacity="0.15" />
              </linearGradient>
            </defs>

            {/* Energy ribbon */}
            <path d={svgPaths} fill="url(#bt-energy)" stroke="none" />

            {/* Beat grid bars */}
            {beatXs.map((x, i) => (
              <line
                key={`b${i}`}
                x1={x}
                x2={x}
                y1={6}
                y2={74}
                stroke="#67e8f9"
                strokeOpacity={0.55}
                strokeWidth={1.5}
              />
            ))}

            {/* Drops -- thicker magenta bars */}
            {dropXs.map((x, i) => (
              <line
                key={`d${i}`}
                x1={x}
                x2={x}
                y1={4}
                y2={76}
                stroke="#ec4899"
                strokeWidth={2}
                opacity={0.9}
              />
            ))}
          </svg>
        )}
      </div>

      {data && (
        <p className="text-[11px] text-gray-500 mt-2 font-mono">
          Cuts will be placed on cyan bars · drops trigger flash/zoom transitions
        </p>
      )}
    </motion.div>
  );
};

export default BeatTimeline;
