'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Rocket, Loader2, CheckCircle2, XCircle, Eye, Activity, Settings, ChevronDown, ChevronUp, Terminal, Download, ExternalLink, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getLead, getLeadPdfExportUrl, getLeadsCsvExportUrl, launchMission } from '@/lib/api';
import { SystemStatus } from './system-status';

interface LogEntry {
  id: string;
  timestamp: Date;
  agent: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
  image_url?: string;
}

interface LeadPreview {
  id: number;
  company: string;
  score: number;
  score_bucket: string;
  role_type: string;
}

type LeadDetails = Awaited<ReturnType<typeof getLead>>;

export function MissionControl() {
  const [input, setInput] = useState('Find startup founders, team size 5-20, need for marketing');
  const [viewState, setViewState] = useState<'initial' | 'active'>('initial');
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [foundLeads, setFoundLeads] = useState<LeadPreview[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('🚀 Founder-Finder Agent (Mission)');
  const [latestImage, setLatestImage] = useState<string | null>(null);
  const [lastStatus, setLastStatus] = useState<string>("Ready");
  const [healthState, setHealthState] = useState<'ok' | 'issue' | 'checking'>('checking');
  const [selectedLead, setSelectedLead] = useState<LeadDetails | null>(null);
  const [selectedLeadLoading, setSelectedLeadLoading] = useState(false);
  const [selectedLeadError, setSelectedLeadError] = useState<string | null>(null);
  
  // Toggles
  const [showStatus, setShowStatus] = useState(false);
  const [showDetails, setShowDetails] = useState(false); // Logs & Vision
  const [showSettings, setShowSettings] = useState(false);

  const logsEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (showDetails) {
      scrollToBottom();
    }
  }, [logs, showDetails]);

  // Auto-run Flight Check on mount
  useEffect(() => {
    const check = async () => {
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001';
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) {
          setHealthState('issue');
          setShowStatus(true); // Auto-open if issue!
        } else {
          const data = await res.json();
          if (data.api !== 'ok' || data.database !== 'ok' || data.ollama.status !== 'ok') {
             setHealthState('issue');
          } else {
             setHealthState('ok');
          }
        }
      } catch (e) {
        setHealthState('issue');
        setShowStatus(true); // Auto-open on connection fail
      }
    };
    check();
  }, []);

  // Listen for real-time events
  useEffect(() => {
    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001';
    const eventSource = new EventSource(`${API_BASE}/api/events`);

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        
        if (parsed.type === 'mission_log') {
          const logData = parsed.data;
          addLog(logData.agent, logData.message, logData.type, logData.image_url);
          setLastStatus(`${logData.agent}: ${logData.message}`);
          
          if (logData.image_url) {
            setLatestImage(logData.image_url);
          }
          
          if (logData.agent === 'Mission Control') {
             if (logData.type === 'success' || logData.type === 'error') {
               setIsRunning(false);
             }
          }
        } else if (parsed.type === 'lead_created') {
          const lead = parsed.data;
          setFoundLeads((prev) => {
            if (lead?.id && prev.some((p) => p.id === lead.id)) {
              return prev;
            }
            return [lead, ...prev];
          });
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const downloadCsv = () => {
    const url = getLeadsCsvExportUrl();
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const downloadLeadPdf = (leadId: number) => {
    const url = getLeadPdfExportUrl(leadId);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const openLeadDetails = async (leadId: number) => {
    setSelectedLead(null);
    setSelectedLeadError(null);
    setSelectedLeadLoading(true);
    try {
      const lead = await getLead(leadId);
      setSelectedLead(lead);
    } catch (e) {
      setSelectedLeadError(e instanceof Error ? e.message : 'Failed to load lead');
    } finally {
      setSelectedLeadLoading(false);
    }
  };

  const addLog = (agent: string, message: string, type: LogEntry['type'] = 'info', image_url?: string) => {
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        timestamp: new Date(),
        agent,
        message,
        type,
        image_url
      },
    ]);
  };

  const handleLaunchMission = async () => {
    if (!input.trim() || isRunning) return;

    const missionPrompt = input;
    setIsRunning(true);
    setViewState('active');
    setLogs([]);
    setFoundLeads([]); 
    setLatestImage(null);
    setLastStatus("Initializing mission agents...");

    try {
      await launchMission(missionPrompt);
    } catch (error) {
      addLog('Mission Control', `Error launching mission: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      setIsRunning(false);
    }
  };

  // Visual Helpers
  const getBucketColor = (bucket: string) => {
    switch (bucket) {
      case 'red_hot': return 'bg-red-500/20 text-red-300 border-red-500/50';
      case 'warm': return 'bg-orange-500/20 text-orange-300 border-orange-500/50';
      case 'nurture': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50';
      default: return 'bg-slate-500/20 text-slate-300 border-slate-500/50';
    }
  };

  const getLogColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return 'text-green-400';
      case 'error': return 'text-red-400';
      case 'warning': return 'text-yellow-400';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background Decoration */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(56,189,248,0.05),transparent_60%)] pointer-events-none" />

      {/* Top Bar */}
      <div className="p-4 flex justify-between items-center z-10">
        <div className="flex items-center gap-2 text-white/50 text-xs">
          <Rocket className="h-4 w-4" /> Raptorflow Agent
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowStatus(true)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
              healthState === 'issue' 
                ? 'bg-red-500/20 text-red-400 border border-red-500/50 animate-pulse' 
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-white'
            }`}
          >
            <Activity className="h-3 w-3" />
            {healthState === 'issue' ? 'Flight Check Failed' : 'Flight Check'}
          </button>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 hover:bg-slate-800 rounded-full transition-colors ${showSettings ? 'text-white bg-slate-800' : 'text-slate-400'}`}
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>

      <SystemStatus isOpen={showStatus} onClose={() => setShowStatus(false)} />

      {/* Settings Panel (Dropdown) */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-slate-900 border-b border-slate-800 overflow-hidden"
          >
            <div className="p-4 max-w-2xl mx-auto">
              <label className="block text-xs text-slate-400 mb-2">Agent Model Strategy</label>
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-white text-sm"
              >
                <option value="🚀 Founder-Finder Agent (Mission)">🚀 Founder-Finder Agent (Mission)</option>
                <option value="gemma3:4b (Raw Reasoning)">gemma3:4b (Raw Reasoning)</option>
                <option value="gemma3:1b (Fast Tasking)">gemma3:1b (Fast Tasking)</option>
              </select>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 relative z-0">
        
        {/* Initial State: Centered Hero */}
        <AnimatePresence mode="wait">
          {viewState === 'initial' && (
            <motion.div 
              key="initial"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="w-full max-w-2xl text-center space-y-8"
            >
              <div>
                <h1 className="text-4xl md:text-5xl font-black text-white mb-4 tracking-tight">
                  Generate Leads <span className="text-blue-500">Autonomously</span>
                </h1>
                <p className="text-slate-400 text-lg">
                  Describe your ideal customer. The agent will find, scrape, and qualify them.
                </p>
              </div>

              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-xl blur opacity-25 group-hover:opacity-50 transition duration-500" />
                <div className="relative flex bg-slate-900 rounded-xl border border-slate-700 overflow-hidden shadow-2xl">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleLaunchMission(); } }}
                    placeholder="Ex: Startup founders in Bangalore, team size 5-20, hiring for marketing..."
                    className="flex-1 bg-transparent text-white p-4 text-lg placeholder:text-slate-600 resize-none focus:outline-none"
                    rows={2}
                  />
                  <div className="p-2 flex flex-col justify-end">
                    <Button
                      onClick={handleLaunchMission}
                      disabled={!input.trim()}
                      className="h-12 w-12 rounded-lg bg-blue-600 hover:bg-blue-500 text-white p-0 flex items-center justify-center"
                    >
                      <Rocket className="h-6 w-6" />
                    </Button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Active State: Top Input + Results */}
          {viewState === 'active' && (
            <motion.div
              key="active"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full max-w-5xl h-full flex flex-col"
            >
              {/* Sticky Header with Input */}
              <div className="flex gap-4 mb-8 items-start">
                <div className="flex-1 bg-slate-900 rounded-lg border border-slate-700 p-3 flex items-center gap-3 shadow-lg">
                  <div className="bg-blue-500/10 p-2 rounded-full">
                    {isRunning ? <Loader2 className="h-5 w-5 text-blue-400 animate-spin" /> : <CheckCircle2 className="h-5 w-5 text-green-400" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-slate-400 text-xs uppercase font-bold mb-0.5">Current Mission</p>
                    <p className="text-white text-sm line-clamp-1">{input}</p>
                  </div>
                  {/* Granular Status Display */}
                  {isRunning && (
                    <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-black/30 rounded text-xs text-blue-300 font-mono border border-blue-500/20">
                      <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                      {lastStatus}
                    </div>
                  )}
                </div>
                <Button
                  onClick={() => { setViewState('initial'); setIsRunning(false); }}
                  variant="outline"
                  className="h-full border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  New
                </Button>
              </div>

              <div className="flex items-center justify-between mb-4">
                <div className="text-xs text-slate-500">
                  {foundLeads.length} leads discovered
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={downloadCsv}
                    variant="outline"
                    className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800"
                  >
                    <Download className="h-4 w-4 mr-2" /> Export CSV
                  </Button>
                </div>
              </div>

              {/* Results Grid */}
              <div className="flex-1 overflow-y-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-20">
                  <AnimatePresence>
                    {foundLeads.map((lead, idx) => {
                      const scoreValue = Number((lead as any)?.score ?? 0) || 0;
                      const progressValue = Math.max(0, Math.min(100, scoreValue));

                      return (
                        <motion.div
                          key={lead.id}
                          initial={{ opacity: 0, scale: 0.9, y: 20 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          transition={{ delay: idx * 0.1 }}
                          className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-blue-500/50 transition-all shadow-lg group"
                        >
                          <div className="flex justify-between items-start mb-3">
                            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-lg font-bold text-slate-300">
                              {(lead.company || 'U').charAt(0)}
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-bold border ${getBucketColor(lead.score_bucket)}`}>
                              {scoreValue.toFixed(0)}
                            </span>
                          </div>

                          <h3 className="font-bold text-white text-lg mb-1 group-hover:text-blue-400 transition-colors">{lead.company || 'Unknown'}</h3>
                          <p className="text-slate-400 text-sm mb-4">{lead.role_type || 'Unknown Role'}</p>

                          <div className="flex items-center gap-2 mb-4">
                            <Button
                              onClick={() => openLeadDetails(lead.id)}
                              variant="outline"
                              className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-900"
                            >
                              <ExternalLink className="h-4 w-4 mr-2" /> View
                            </Button>
                            <Button
                              onClick={() => downloadLeadPdf(lead.id)}
                              variant="outline"
                              className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-900"
                            >
                              <FileText className="h-4 w-4 mr-2" /> PDF
                            </Button>
                          </div>

                          <div className="w-full bg-slate-700/50 h-1.5 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${progressValue}%` }}
                              className={`h-full rounded-full ${scoreValue > 80 ? 'bg-red-500' : scoreValue > 60 ? 'bg-orange-500' : 'bg-blue-500'}`}
                            />
                          </div>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                  
                  {foundLeads.length === 0 && (
                    <div className="col-span-full flex flex-col items-center justify-center py-20 text-slate-500">
                      <div className="relative">
                        <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse" />
                        <Rocket className="h-16 w-16 mb-4 text-blue-400 relative z-10 animate-bounce" />
                      </div>
                      <p className="text-lg font-medium text-slate-300 animate-pulse">{lastStatus}</p>
                      <p className="text-xs text-slate-500 mt-2">The agent is working...</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Collapsible Details Drawer (Logs + Vision) */}
              <motion.div 
                className="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800 shadow-2xl z-20"
                animate={{ height: showDetails ? '350px' : '40px' }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              >
                <button 
                  onClick={() => setShowDetails(!showDetails)}
                  className="w-full h-10 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors uppercase tracking-wider border-b border-slate-800"
                >
                  {showDetails ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
                  {showDetails ? 'Hide' : 'Show'} Agent Activity & Vision
                </button>

                <div className="flex h-full pb-10">
                  {/* Logs */}
                  <div className="flex-1 border-r border-slate-800 p-4 overflow-y-auto font-mono text-xs space-y-2 bg-black/20">
                    <div className="flex items-center gap-2 text-slate-500 mb-2">
                      <Terminal className="h-3 w-3" /> Agent Logs
                    </div>
                    {logs.map((log) => (
                      <div key={log.id} className="flex gap-2">
                        <span className="text-slate-600">[{log.timestamp.toLocaleTimeString().split(' ')[0]}]</span>
                        <span className={getLogColor(log.type)}>{log.message}</span>
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>

                  {/* Vision */}
                  <div className="w-1/3 p-4 bg-slate-950 flex flex-col">
                    <div className="flex items-center gap-2 text-slate-500 mb-2">
                      <Eye className="h-3 w-3" /> Live Vision
                    </div>
                    <div className="flex-1 border border-slate-800 rounded bg-slate-900 flex items-center justify-center overflow-hidden relative">
                      {latestImage ? (
                        <>
                          <img src={latestImage} alt="Vision" className="max-w-full max-h-full object-contain opacity-80" />
                          <div className="absolute top-2 right-2 h-2 w-2 bg-red-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                        </>
                      ) : (
                        <span className="text-slate-700 italic">No visual signal</span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>

              <AnimatePresence>
                {(selectedLeadLoading || selectedLead || selectedLeadError) && (
                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="fixed top-16 right-6 w-[420px] max-w-[90vw] bg-slate-950 border border-slate-800 rounded-xl shadow-2xl z-30 overflow-hidden"
                  >
                    <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                      <div className="text-sm font-bold text-white">Lead Details</div>
                      <button
                        onClick={() => { setSelectedLead(null); setSelectedLeadError(null); setSelectedLeadLoading(false); }}
                        className="text-slate-400 hover:text-white"
                      >
                        <XCircle className="h-5 w-5" />
                      </button>
                    </div>

                    <div className="p-4 space-y-3">
                      {selectedLeadLoading && (
                        <div className="text-slate-400 text-sm flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" /> Loading...
                        </div>
                      )}

                      {selectedLeadError && (
                        <div className="text-red-400 text-sm">{selectedLeadError}</div>
                      )}

                      {selectedLead && (
                        <>
                          <div>
                            <div className="text-white font-bold text-lg">{selectedLead.company?.name || 'Unknown'}</div>
                            <div className="text-slate-400 text-xs">Score: {selectedLead.total_score?.toFixed?.(0) ?? selectedLead.total_score} ({selectedLead.score_bucket})</div>
                          </div>

                          <div className="space-y-1 text-sm">
                            <div className="text-slate-300">
                              <span className="text-slate-500">Website:</span>{' '}
                              {selectedLead.company?.website ? (
                                <a className="text-blue-400 hover:underline" href={selectedLead.company.website} target="_blank" rel="noreferrer">{selectedLead.company.website}</a>
                              ) : (
                                <span className="text-slate-500">—</span>
                              )}
                            </div>
                            <div className="text-slate-300">
                              <span className="text-slate-500">Contact:</span>{' '}
                              {selectedLead.contact?.name || '—'}
                            </div>
                            <div className="text-slate-300">
                              <span className="text-slate-500">Email:</span>{' '}
                              {selectedLead.contact?.email || '—'}
                            </div>
                            <div className="text-slate-300">
                              <span className="text-slate-500">Phone(s):</span>{' '}
                              {(selectedLead.contact?.phone_numbers || []).join(', ') || '—'}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 pt-2">
                            <Button
                              onClick={() => downloadLeadPdf(selectedLead.id)}
                              variant="outline"
                              className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-900"
                            >
                              <FileText className="h-4 w-4 mr-2" /> Download PDF
                            </Button>
                            <Button
                              onClick={downloadCsv}
                              variant="outline"
                              className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-900"
                            >
                              <Download className="h-4 w-4 mr-2" /> CSV
                            </Button>
                          </div>
                        </>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
