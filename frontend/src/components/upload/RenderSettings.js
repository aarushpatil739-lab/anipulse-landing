import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Smartphone,
  Square,
  Monitor,
  Sparkles,
  Film,
  Heart,
  Zap,
  Flame,
  Skull,
} from 'lucide-react';

/**
 * RenderSettings
 * --------------
 * Two stacked controls:
 *   1. Edit Preset  -- drives pacing + transition + effect density
 *      (Cinematic / Emotional / Velocity / Phonk / Aggressive)
 *   2. Output Format -- 16:9 / 9:16 / 1:1  + (for non-16:9) a TikTok-style
 *      blurred-background vs centre-crop toggle.
 *
 * Props:
 *   preset / onPresetChange         : string, (v)=>void
 *   aspectRatio / onAspectRatioChange : string, (v)=>void
 *   verticalMode / onVerticalModeChange : string, (v)=>void
 *   disabled : boolean
 */

const PRESETS = [
  {
    value: 'cinematic',
    label: 'Cinematic',
    sub: 'Longer holds · classic AMV',
    Icon: Film,
    accent: 'cyan',
  },
  {
    value: 'emotional',
    label: 'Emotional',
    sub: 'Slow burn · fade transitions',
    Icon: Heart,
    accent: 'pink',
  },
  {
    value: 'velocity',
    label: 'Velocity',
    sub: 'Fast cuts · high energy',
    Icon: Zap,
    accent: 'violet',
  },
  {
    value: 'phonk',
    label: 'Phonk',
    sub: 'Hard cuts · drift-edit feel',
    Icon: Skull,
    accent: 'amber',
  },
  {
    value: 'aggressive',
    label: 'Aggressive',
    sub: 'Maximum cuts + effects',
    Icon: Flame,
    accent: 'rose',
  },
];

const RATIOS = [
  { value: '16:9', label: 'Widescreen', sub: 'YouTube · 16:9', Icon: Monitor, accent: 'cyan' },
  { value: '9:16', label: 'Vertical', sub: 'TikTok · Reels · Shorts', Icon: Smartphone, accent: 'pink' },
  { value: '1:1', label: 'Square', sub: 'Instagram feed', Icon: Square, accent: 'violet' },
];

const MODES = [
  { value: 'blurred', label: 'Blurred background', sub: 'TikTok-style · keeps full frame' },
  { value: 'crop', label: 'Center crop', sub: 'Zooms to fill · may cut edges' },
];

const ACCENTS = {
  cyan: 'ring-cyan-400 from-cyan-500/20 to-blue-500/5 text-cyan-200',
  pink: 'ring-pink-400 from-pink-500/20 to-purple-500/5 text-pink-200',
  violet: 'ring-violet-400 from-violet-500/20 to-fuchsia-500/5 text-violet-200',
  amber: 'ring-amber-400 from-amber-500/20 to-orange-500/5 text-amber-200',
  rose: 'ring-rose-400 from-rose-500/20 to-red-500/5 text-rose-200',
};

const Tile = ({ active, accent, disabled, onClick, children, testId }) => (
  <button
    type="button"
    data-testid={testId}
    disabled={disabled}
    onClick={onClick}
    className={`group relative rounded-xl p-4 text-left transition-all border bg-gradient-to-br ${
      active
        ? `ring-2 ${ACCENTS[accent]} border-transparent`
        : 'border-white/10 bg-white/[0.02] text-gray-300 hover:bg-white/[0.05] hover:border-white/20'
    } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
  >
    {children}
  </button>
);

const RenderSettings = ({
  preset = 'cinematic',
  onPresetChange,
  aspectRatio = '16:9',
  onAspectRatioChange,
  verticalMode = 'blurred',
  onVerticalModeChange,
  disabled = false,
}) => {
  const showVerticalMode = aspectRatio === '9:16' || aspectRatio === '1:1';

  return (
    <motion.div
      data-testid="render-settings"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-effect rounded-2xl p-6 border border-purple-400/20"
    >
      {/* === Edit Preset === */}
      <div className="flex items-center gap-2 mb-4 text-purple-300">
        <Sparkles className="w-4 h-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wider">Edit Style</h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-7">
        {PRESETS.map(({ value, label, sub, Icon, accent }) => {
          const active = preset === value;
          return (
            <Tile
              key={value}
              active={active}
              accent={accent}
              disabled={disabled}
              onClick={() => onPresetChange?.(value)}
              testId={`preset-${value}`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className="w-5 h-5" />
              </div>
              <div className="font-semibold text-sm leading-tight">{label}</div>
              <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
            </Tile>
          );
        })}
      </div>

      {/* === Output Format === */}
      <div className="flex items-center gap-2 mb-4 text-purple-300">
        <Monitor className="w-4 h-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wider">Output Format</h3>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        {RATIOS.map(({ value, label, sub, Icon, accent }) => {
          const active = aspectRatio === value;
          return (
            <Tile
              key={value}
              active={active}
              accent={accent}
              disabled={disabled}
              onClick={() => onAspectRatioChange?.(value)}
              testId={`ar-option-${value.replace(':', 'x')}`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className="w-5 h-5" />
                <span className="font-mono text-[11px] opacity-70">{value}</span>
              </div>
              <div className="font-semibold text-sm leading-tight">{label}</div>
              <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
            </Tile>
          );
        })}
      </div>

      <AnimatePresence initial={false}>
        {showVerticalMode && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="text-xs uppercase tracking-wider text-gray-400 mb-2">Fit mode</div>
            <div className="grid grid-cols-2 gap-3">
              {MODES.map(({ value, label, sub }) => {
                const active = verticalMode === value;
                return (
                  <button
                    type="button"
                    key={value}
                    data-testid={`vmode-${value}`}
                    disabled={disabled}
                    onClick={() => onVerticalModeChange?.(value)}
                    className={`rounded-xl p-3 text-left transition-all border ${
                      active
                        ? 'border-pink-400 bg-pink-500/10 text-pink-100'
                        : 'border-white/10 bg-white/[0.02] text-gray-300 hover:bg-white/[0.05]'
                    } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <div className="font-semibold text-sm">{label}</div>
                    <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default RenderSettings;
