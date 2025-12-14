'use client';

import { useEffect, useState } from 'react';
import { Loader2, Activity, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { getBucketCounts } from '@/lib/api';

interface BucketCounts {
  red_hot: number;
  warm: number;
  nurture: number;
  parked: number;
}

const BUCKET_INFO = {
  red_hot: {
    emoji: '🔥',
    name: 'Red Hot',
    description: 'Immediate attention (80-100)',
    color: 'from-red-600 to-red-500',
    textColor: 'text-red-300',
  },
  warm: {
    emoji: '🔆',
    name: 'Warm',
    description: 'This week (60-79)',
    color: 'from-orange-600 to-orange-500',
    textColor: 'text-orange-300',
  },
  nurture: {
    emoji: '👀',
    name: 'Nurture',
    description: 'Keep watching (40-59)',
    color: 'from-yellow-600 to-yellow-500',
    textColor: 'text-yellow-300',
  },
  parked: {
    emoji: '📦',
    name: 'Parked',
    description: 'Not a fit (<40)',
    color: 'from-slate-600 to-slate-500',
    textColor: 'text-slate-300',
  },
};

export default function Dashboard() {
  const [counts, setCounts] = useState<BucketCounts>({
    red_hot: 0,
    warm: 0,
    nurture: 0,
    parked: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCounts = async () => {
    try {
      const data = await getBucketCounts();
      setCounts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCounts();
    const interval = setInterval(fetchCounts, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const totalLeads = counts.red_hot + counts.warm + counts.nurture + counts.parked;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-700 border border-slate-600 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Lead Pipeline</h1>
            <p className="text-slate-400 mt-1">
              Overview of all qualified leads by score bucket
            </p>
          </div>
          <Activity className="h-12 w-12 text-blue-400 opacity-50" />
        </div>
      </div>

      {/* Metrics Grid */}
      {error ? (
        <div className="flex gap-2 text-red-400 text-sm p-4 bg-red-500/10 border border-red-500/50 rounded">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 text-blue-400 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(BUCKET_INFO).map(([bucket, info], idx) => {
              const count = counts[bucket as keyof BucketCounts];
              const percentage = totalLeads > 0 ? (count / totalLeads) * 100 : 0;

              return (
                <motion.div
                  key={bucket}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`bg-gradient-to-br ${info.color} rounded-lg p-6 border border-opacity-20 border-white`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-3xl">{info.emoji}</span>
                    <span className="text-xs font-semibold text-white/80 uppercase">
                      {percentage.toFixed(0)}%
                    </span>
                  </div>

                  <h3 className="text-white font-bold text-lg mb-1">{info.name}</h3>
                  <p className="text-white/70 text-xs mb-4">{info.description}</p>

                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-white">{count}</span>
                    <span className="text-white/60 text-sm">leads</span>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-4 h-1 bg-white/20 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${percentage}%` }}
                      transition={{ delay: 0.5 + idx * 0.1, duration: 0.8 }}
                      className="h-full bg-white/60 rounded-full"
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Summary Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-slate-800 border border-slate-700 rounded-lg p-6"
          >
            <h2 className="text-lg font-bold text-white mb-4">Summary</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-slate-400 text-sm mb-2">Total Leads</p>
                <p className="text-3xl font-bold text-white">{totalLeads}</p>
              </div>

              <div>
                <p className="text-slate-400 text-sm mb-2">Action Required</p>
                <p className="text-3xl font-bold text-red-400">
                  {counts.red_hot + counts.warm}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {totalLeads > 0
                    ? (((counts.red_hot + counts.warm) / totalLeads) * 100).toFixed(1)
                    : 0}
                  % urgent
                </p>
              </div>

              <div>
                <p className="text-slate-400 text-sm mb-2">Active Pipeline</p>
                <div className="flex items-end gap-2">
                  <p className="text-3xl font-bold text-green-400">
                    {counts.red_hot + counts.warm + counts.nurture}
                  </p>
                  <p className="text-slate-400 text-xs pb-1 mb-1">
                     ({totalLeads > 0 ? Math.round(((counts.red_hot + counts.warm + counts.nurture) / totalLeads) * 100) : 0}%)
                  </p>
                </div>
                <p className="text-xs text-slate-500 mt-1">Excludes parked</p>
              </div>
            </div>
          </motion.div>

          {/* Tips */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4"
          >
            <p className="text-sm text-blue-300">
              <span className="font-semibold">💡 Tip:</span> Focus on red hot leads first. These show
              clear marketing pain and are ready for outreach now.
            </p>
          </motion.div>
        </>
      )}
    </div>
  );
}
