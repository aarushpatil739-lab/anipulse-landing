import React from 'react';
import { motion } from 'framer-motion';
import { Smartphone, Square, Monitor, Sparkles } from 'lucide-react';

/**
 * RenderSettings
 * --------------
 * Lets the creator pick the output aspect ratio (16:9, 9:16, 1:1) and
 * -- when relevant -- the "fit" mode used by the renderer to fit a 16:9
 * source into a vertical / square frame.
 *
 * Props:
 *   aspectRatio       : '16:9' | '9:16' | '1:1'
 *   onAspectRatioChange: (val) => void
 *   verticalMode      : 'blurred' | 'crop'
 *   onVerticalModeChange: (val) => void
 *   disabled          : boolean -- gray out while a render is in flight
 */
const RATIOS = [
  {
    value: '16:9',
    label: 'Widescreen',
    sub: 'YouTube · 16:9',
    Icon: Monitor,
    accent: 'cyan',
  },
  {
    value: '9:16',
    label: 'Vertical',
    sub: 'TikTok · Reels · Shorts',
    Icon: Smartphone,
    accent: 'pink',
  },
  {
    value: '1:1',
    label: 'Square',
    sub: 'Instagram feed',
    Icon: Square,
    accent: 'violet',
  },
];

const MODES = [
  {
    value: 'blurred',
    label: 'Blurred background',
    sub: 'TikTok-style · keeps full frame',
  },
  {
    value: 'crop',
    label: 'Center crop',
    sub: 'Zooms to fill · may cut edges',
  },
];

const RenderSettings = ({
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
      <div className="flex items-center gap-2 mb-4 text-purple-300">
        <Sparkles className="w-4 h-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wider">
          Output Format
        </h3>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        {RATIOS.map(({ value, label, sub, Icon, accent }) => {
          const active = aspectRatio === value;
          const accentRing = {
            cyan: 'ring-cyan-400 from-cyan-500/20 to-blue-500/5 text-cyan-200',
            pink: 'ring-pink-400 from-pink-500/20 to-purple-500/5 text-pink-200',
            violet: 'ring-violet-400 from-violet-500/20 to-fuchsia-500/5 text-violet-200',
          }[accent];
          return (
            <button
              type="button"
              key={value}
              data-testid={`ar-option-${value.replace(':', 'x')}`}
              disabled={disabled}
              onClick={() => onAspectRatioChange?.(value)}
              className={`group relative rounded-xl p-4 text-left transition-all border bg-gradient-to-br ${
                active
                  ? `ring-2 ${accentRing} border-transparent`
                  : 'border-white/10 bg-white/[0.02] text-gray-300 hover:bg-white/[0.05] hover:border-white/20'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className="w-5 h-5" />
                <span className="font-mono text-[11px] opacity-70">{value}</span>
              </div>
              <div className="font-semibold text-sm leading-tight">{label}</div>
              <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
            </button>
          );
        })}
      </div>

      {showVerticalMode && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="overflow-hidden"
        >
          <div className="text-xs uppercase tracking-wider text-gray-400 mb-2">
            Fit mode
          </div>
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
    </motion.div>
  );
};

export default RenderSettings;
