'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, XCircle, AlertCircle, RefreshCw, Server, Database, Brain, Globe } from 'lucide-react';
import { getSystemHealth, type SystemHealth } from '@/lib/api';

export function SystemStatus({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const data = await getSystemHealth();
      setHealth(data);
    } catch (err) {
      console.error('Health check failed:', err);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      checkHealth();
    }
  }, [isOpen]);

  const StatusItem = ({ 
    label, 
    status, 
    icon: Icon, 
    details 
  }: { 
    label: string; 
    status: 'ok' | 'error' | 'warning'; 
    icon: any;
    details?: string;
  }) => (
    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-full ${
          status === 'ok' ? 'bg-green-500/10 text-green-400' : 
          status === 'error' ? 'bg-red-500/10 text-red-400' : 
          'bg-yellow-500/10 text-yellow-400'
        }`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="font-medium text-white">{label}</p>
          {details && <p className="text-xs text-slate-400">{details}</p>}
        </div>
      </div>
      {status === 'ok' ? (
        <CheckCircle2 className="h-5 w-5 text-green-500" />
      ) : status === 'error' ? (
        <XCircle className="h-5 w-5 text-red-500" />
      ) : (
        <AlertCircle className="h-5 w-5 text-yellow-500" />
      )}
    </div>
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md shadow-2xl overflow-hidden"
          >
            <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-900">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                System Flight Check
              </h2>
              <button onClick={onClose} className="text-slate-400 hover:text-white">
                <XCircle className="h-6 w-6" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {loading && !health ? (
                <div className="text-center py-8 text-slate-400">Running diagnostics...</div>
              ) : health ? (
                <>
                  <StatusItem 
                    label="Backend API" 
                    status={health.api === 'ok' ? 'ok' : 'error'} 
                    icon={Server} 
                    details={health.api === 'ok' ? 'Online' : 'Unreachable'}
                  />
                  
                  <StatusItem 
                    label="Database" 
                    status={health.database === 'ok' ? 'ok' : 'error'} 
                    icon={Database} 
                    details={health.database === 'ok' ? 'Connected' : 'Connection Failed'}
                  />

                  <StatusItem 
                    label="Ollama AI" 
                    status={health.ollama.status === 'ok' ? 'ok' : 'error'} 
                    icon={Brain} 
                    details={
                      health.ollama.status === 'ok' 
                      ? `Models: ${health.ollama.models['1b'] ? '1B ✓' : '1B ✗'}, ${health.ollama.models['4b'] ? '4B ✓' : '4B ✗'}`
                      : 'Service Offline (Run OllamaSetup.exe)'
                    }
                  />

                  <StatusItem 
                    label="Agent Tools" 
                    status={health.scraping?.browsers_installed ? 'ok' : 'warning'} 
                    icon={Globe} 
                    details={
                      health.scraping?.browsers_installed 
                      ? 'Browsers & Search Tools Ready' 
                      : 'Browsers Missing (Install Playwright for Deep Scrape)'
                    }
                  />
                </>
              ) : (
                <div className="text-center py-8 text-red-400">
                  <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>System Unreachable</p>
                  <p className="text-xs mt-2">Ensure the backend server is running on port 8001</p>
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-950 border-t border-slate-800 text-center">
              <p className="text-xs text-slate-500">
                Run <code className="bg-slate-800 px-1 rounded">python backend/main.py</code> to start server
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
