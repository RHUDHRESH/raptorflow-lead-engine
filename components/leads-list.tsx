'use client';

import { useEffect, useState, useRef } from 'react';
import { AlertCircle, Loader2, Eye, Trash2, Copy, Search, Filter, Download, Upload, Phone, Mail, Globe, MessageSquare, Clock, ChevronRight, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  listLeads, 
  getLead, 
  updateLeadStatus, 
  deleteLead, 
  advancedLeadSearch, 
  ingestCSV, 
  updateLeadNotes,
  type Lead, 
  type LeadFilter 
} from '@/lib/api';
import { AdvancedSearch } from './advanced-search';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function LeadsList() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [searchMode, setSearchMode] = useState<'simple' | 'advanced'>('simple');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [scoreFilter, setScoreFilter] = useState(60);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [bucketFilter, setBucketFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [leadDetailsLoading, setLeadDetailsLoading] = useState(false);
  
  // CSV Import
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{processed: number, created: number} | null>(null);

  // Note Input
  const [noteInput, setNoteInput] = useState('');
  const [noteSaving, setNoteSaving] = useState(false);

  // Dossier Modal
  const [showFullDossier, setShowFullDossier] = useState(false);

  // Detail Tabs State
  const [activeTab, setActiveTab] = useState("overview");

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      // If text search is active, use advanced search
      if (searchQuery) {
        const filters: LeadFilter = {
          score_min: scoreFilter,
          status: statusFilter || undefined,
          score_bucket: bucketFilter || undefined,
          company_name_contains: searchQuery,
          limit: 50,
        };
        const data = await advancedLeadSearch(filters);
        setLeads(data);
      } else {
        // Otherwise use standard list
        const data = await listLeads({
          score_min: scoreFilter,
          status: statusFilter || undefined,
          score_bucket: bucketFilter || undefined,
          limit: 50,
        });
        setLeads(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchLeadDetails = async (id: number) => {
    setLeadDetailsLoading(true);
    try {
      const lead = await getLead(id);
      setSelectedLead(lead);
    } catch (err) {
      console.error('Failed to fetch lead details:', err);
    } finally {
      setLeadDetailsLoading(false);
    }
  };

  const handleAdvancedSearch = async (filters: any) => {
    setLoading(true);
    setError(null);
    try {
      const data = await advancedLeadSearch(filters);
      setLeads(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    window.open(`${API_BASE}/api/leads/export/csv`, '_blank');
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await ingestCSV(file);
      setImportResult({
        processed: result.total_processed,
        created: result.total_created
      });
      fetchLeads(); // Refresh list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setImporting(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleAddNote = async () => {
    if (!selectedLead || !noteInput.trim()) return;
    setNoteSaving(true);
    try {
      await updateLeadNotes(selectedLead.id, noteInput);
      setNoteInput('');
      // Refresh details to show new note/activity
      await fetchLeadDetails(selectedLead.id);
    } catch (err) {
      console.error('Failed to add note:', err);
      alert('Failed to add note');
    } finally {
      setNoteSaving(false);
    }
  };

  useEffect(() => {
    if (searchMode === 'simple') {
      const debounce = setTimeout(fetchLeads, 500);
      return () => clearTimeout(debounce);
    }
  }, [scoreFilter, statusFilter, bucketFilter, searchQuery, searchMode]);

  const getBucketColor = (bucket: string) => {
    switch (bucket) {
      case 'red_hot': return 'bg-red-500/20 text-red-300 border-red-500/50';
      case 'warm': return 'bg-orange-500/20 text-orange-300 border-orange-500/50';
      case 'nurture': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50';
      default: return 'bg-slate-500/20 text-slate-300 border-slate-500/50';
    }
  };

  const getBucketEmoji = (bucket: string) => {
    switch (bucket) {
      case 'red_hot': return '🔥';
      case 'warm': return '🔆';
      case 'nurture': return '👀';
      default: return '📦';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex gap-2">
          <button
            onClick={() => setSearchMode('simple')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
              searchMode === 'simple'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-slate-700 text-slate-400 border-slate-600 hover:bg-slate-600'
            }`}
          >
            <Search className="h-4 w-4" />
            Pipeline Search
          </button>
          <button
            onClick={() => setSearchMode('advanced')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
              searchMode === 'advanced'
                ? 'bg-purple-600 text-white border-purple-600'
                : 'bg-slate-700 text-slate-400 border-slate-600 hover:bg-slate-600'
            }`}
          >
            <Filter className="h-4 w-4" />
            Executive Finder
          </button>
        </div>

        <div className="flex gap-2">
           <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".csv"
              className="hidden"
            />
          <button
            onClick={handleImportClick}
            disabled={importing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-600 bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
          >
            {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Import CSV
          </button>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-600 bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {importResult && (
        <div className="bg-green-500/10 border border-green-500/50 p-4 rounded-lg flex items-center justify-between text-green-300">
          <span>Successfully processed {importResult.processed} rows, created {importResult.created} new leads.</span>
          <button onClick={() => setImportResult(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Filters (Simple Mode) */}
      {searchMode === 'simple' && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Search Company</label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-500" />
                <input 
                  type="text" 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Acme Corp..."
                  className="w-full pl-8 pr-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Status</label>
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">All Statuses</option>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="pitched">Pitched</option>
                <option value="won">Won</option>
                <option value="lost">Lost</option>
                <option value="parked">Parked</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Bucket</label>
              <select 
                value={bucketFilter} 
                onChange={(e) => setBucketFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">All Buckets</option>
                <option value="red_hot">🔥 Red Hot</option>
                <option value="warm">🔆 Warm</option>
                <option value="nurture">👀 Nurture</option>
                <option value="parked">📦 Parked</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Min Score: {scoreFilter}</label>
              <input
                type="range"
                min="0"
                max="150"
                value={scoreFilter}
                onChange={(e) => setScoreFilter(Number(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        </div>
      )}

      {/* Advanced Search Component */}
      {searchMode === 'advanced' && (
        <AdvancedSearch
          onSearch={handleAdvancedSearch}
          loading={loading}
        />
      )}

      {/* Results Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Leads List */}
        <div className={`lg:col-span-2 ${selectedLead ? 'hidden lg:block' : ''}`}>
          <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden flex flex-col h-[600px]">
            <div className="bg-slate-900 border-b border-slate-700 p-4 flex justify-between items-center">
              <div>
                <h2 className="text-lg font-bold text-white">
                  {searchMode === 'simple' ? 'Pipeline' : 'Search Results'}
                </h2>
                <p className="text-xs text-slate-400">
                  {leads.length} leads found
                </p>
              </div>
              {loading && <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />}
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {error && (
                <div className="p-4 text-red-400 bg-red-500/10 border border-red-500/50 rounded text-sm">
                  {error}
                </div>
              )}

              {!loading && leads.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-500">
                  <Search className="h-12 w-12 mb-2 opacity-20" />
                  <p>No leads found matching your criteria</p>
                </div>
              )}

              {leads.map((lead) => (
                <div
                  key={lead.id}
                  onClick={() => fetchLeadDetails(lead.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedLead?.id === lead.id
                      ? 'bg-blue-600/20 border-blue-500 ring-1 ring-blue-500'
                      : 'bg-slate-700/30 border-slate-700 hover:bg-slate-700 hover:border-slate-600'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-bold text-white text-sm">{lead.company?.name || 'Unknown Company'}</h3>
                      <p className="text-xs text-slate-400">{lead.role_type || lead.economic_buyer_guess || 'Unknown Role'}</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-1 rounded border ${getBucketColor(lead.score_bucket)}`}>
                        {getBucketEmoji(lead.score_bucket)} {Math.round(lead.total_score)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap gap-1 mb-2">
                    {lead.pain_tags?.slice(0, 3).map(tag => (
                      <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                  
                  <div className="flex justify-between items-center text-xs text-slate-500">
                    <span>{lead.status.toUpperCase()}</span>
                    <span>{new Date(lead.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Lead Detail View */}
        <div className={`lg:col-span-1 ${!selectedLead ? 'hidden lg:block' : ''} fixed inset-0 z-50 lg:static lg:z-0 bg-slate-900 lg:bg-transparent overflow-y-auto`}>
          {selectedLead ? (
            <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden h-full lg:h-[600px] flex flex-col shadow-2xl lg:shadow-none">
              {/* Detail Header */}
              <div className="bg-slate-900 p-4 border-b border-slate-700 sticky top-0 z-10 flex justify-between items-start">
                 <div className="flex-1">
                   <button 
                     onClick={() => setSelectedLead(null)}
                     className="lg:hidden text-slate-400 hover:text-white mb-2"
                   >
                     ← Back to list
                   </button>
                   <h2 className="text-xl font-bold text-white">{selectedLead.company?.name}</h2>
                   {selectedLead.company?.website && (
                     <a href={selectedLead.company.website} target="_blank" rel="noreferrer" className="text-blue-400 text-xs hover:underline flex items-center gap-1">
                       <Globe className="h-3 w-3" /> {selectedLead.company.website}
                     </a>
                   )}
                 </div>
                 <div className="flex flex-col items-end gap-2">
                   <div className={`text-lg font-bold px-3 py-1 rounded border ${getBucketColor(selectedLead.score_bucket)}`}>
                     {selectedLead.total_score.toFixed(0)}
                   </div>
                   <select
                      value={selectedLead.status}
                      onChange={async (e) => {
                        const newStatus = e.target.value;
                        try {
                          await updateLeadStatus(selectedLead.id, newStatus);
                          setSelectedLead({...selectedLead, status: newStatus});
                          fetchLeadDetails(selectedLead.id); // Get updated activity
                        } catch(err) { console.error(err); }
                      }}
                      className="bg-slate-700 text-white text-xs px-2 py-1 rounded border border-slate-600 outline-none focus:border-blue-500"
                    >
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="qualified">Qualified</option>
                      <option value="pitched">Pitched</option>
                      <option value="won">Won</option>
                      <option value="lost">Lost</option>
                      <option value="parked">Parked</option>
                    </select>
                 </div>
              </div>

              <div className="flex-1 overflow-y-auto">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="w-full justify-start rounded-none bg-slate-800 border-b border-slate-700 p-0">
                    <TabsTrigger value="overview" className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-slate-800">Overview</TabsTrigger>
                    <TabsTrigger value="analysis" className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-slate-800">Analysis</TabsTrigger>
                    <TabsTrigger value="activity" className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-slate-800">Activity</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" className="p-4 space-y-6">
                    {/* Contacts */}
                    <section>
                      <h3 className="text-xs font-bold text-slate-400 uppercase mb-3 flex items-center gap-2">
                        <Phone className="h-3 w-3" /> Contact Info
                      </h3>
                      <div className="bg-slate-700/30 rounded-lg p-3 space-y-3">
                        {selectedLead.contact?.email ? (
                           <div className="flex items-center gap-2 text-sm">
                             <Mail className="h-4 w-4 text-slate-400" />
                             <a href={`mailto:${selectedLead.contact.email}`} className="text-blue-400 hover:underline">{selectedLead.contact.email}</a>
                           </div>
                        ) : <p className="text-xs text-slate-500 italic">No email found</p>}
                        
                        {selectedLead.contact?.phone_numbers && selectedLead.contact.phone_numbers.length > 0 ? (
                          selectedLead.contact.phone_numbers.map(phone => (
                            <div key={phone} className="flex items-center gap-2 text-sm text-slate-300">
                              <Phone className="h-4 w-4 text-slate-400" />
                              <span>{phone}</span>
                            </div>
                          ))
                        ) : <p className="text-xs text-slate-500 italic">No phone numbers found</p>}
                        
                        <div className="text-xs text-slate-400 pt-2 border-t border-slate-700">
                          <p>Decision Maker: <span className="text-white">{selectedLead.economic_buyer_guess || 'Unknown'}</span></p>
                        </div>
                      </div>
                    </section>

                    {/* Signals */}
                    <section>
                      <h3 className="text-xs font-bold text-slate-400 uppercase mb-3 flex items-center gap-2">
                        <Search className="h-3 w-3" /> Detected Signals
                      </h3>
                      <div className="space-y-2">
                        {selectedLead.signals && selectedLead.signals.length > 0 ? (
                          selectedLead.signals.map(signal => (
                            <div key={signal.id} className="text-xs bg-slate-700/50 p-2 rounded border border-slate-700">
                              <span className="font-mono text-blue-400 bg-blue-900/30 px-1 rounded mr-2">
                                {signal.source_type}
                              </span>
                              <span className="text-slate-400">{new Date(signal.created_at).toLocaleDateString()}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-slate-500">No raw signals linked</p>
                        )}
                      </div>
                    </section>
                  </TabsContent>

                  <TabsContent value="analysis" className="p-4 space-y-6">
                    {/* Pain Tags */}
                    <div className="flex flex-wrap gap-2">
                       {selectedLead.pain_tags?.map(tag => (
                         <span key={tag} className="text-xs px-2 py-1 bg-red-500/10 text-red-300 border border-red-500/30 rounded-full">
                           {tag}
                         </span>
                       ))}
                    </div>

                    {/* SPIN Analysis */}
                    <section className="space-y-4">
                      <div className="space-y-1">
                        <h4 className="text-xs font-bold text-slate-400 uppercase">Situation</h4>
                        <p className="text-sm text-slate-300 leading-relaxed">{selectedLead.situation || 'N/A'}</p>
                      </div>
                      <div className="space-y-1">
                        <h4 className="text-xs font-bold text-slate-400 uppercase">Problem</h4>
                        <p className="text-sm text-slate-300 leading-relaxed">{selectedLead.problem || 'N/A'}</p>
                      </div>
                      <div className="space-y-1">
                        <h4 className="text-xs font-bold text-slate-400 uppercase">Implication</h4>
                        <p className="text-sm text-slate-300 leading-relaxed">{selectedLead.implication || 'N/A'}</p>
                      </div>
                      <div className="space-y-1">
                        <h4 className="text-xs font-bold text-slate-400 uppercase">Need-Payoff</h4>
                        <p className="text-sm text-slate-300 leading-relaxed">{selectedLead.need_payoff || 'N/A'}</p>
                      </div>
                    </section>

                    {/* Dossier Preview */}
                    <section className="bg-slate-700/30 p-4 rounded-lg border border-slate-700">
                      <h3 className="text-sm font-bold text-white mb-2">🤖 AI Context Dossier</h3>
                      <p className="text-xs text-slate-300 line-clamp-4 mb-3">
                        {selectedLead.context_dossier || 'No dossier generated yet.'}
                      </p>
                      {selectedLead.context_dossier && (
                        <button 
                          onClick={() => setShowFullDossier(true)}
                          className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
                        >
                          Read Full Dossier <ChevronRight className="h-3 w-3" />
                        </button>
                      )}
                    </section>
                  </TabsContent>

                  <TabsContent value="activity" className="p-4 flex flex-col h-[450px]">
                    {/* Activity Feed */}
                    <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
                      {selectedLead.activities && selectedLead.activities.length > 0 ? (
                        selectedLead.activities.sort((a,b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).map(activity => (
                          <div key={activity.id} className="flex gap-3 text-sm">
                            <div className="mt-1">
                              {activity.type === 'note' ? (
                                <MessageSquare className="h-4 w-4 text-blue-400" />
                              ) : (
                                <Clock className="h-4 w-4 text-slate-500" />
                              )}
                            </div>
                            <div>
                              <div className="text-xs text-slate-500 mb-0.5">
                                {new Date(activity.timestamp).toLocaleString()}
                              </div>
                              <p className={`text-slate-300 ${activity.type === 'status_change' ? 'italic text-slate-400' : ''}`}>
                                {activity.content}
                              </p>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-center text-slate-500 text-sm py-8">No activity recorded</p>
                      )}
                    </div>

                    {/* Add Note */}
                    <div className="mt-auto pt-4 border-t border-slate-700">
                      <textarea
                        value={noteInput}
                        onChange={(e) => setNoteInput(e.target.value)}
                        placeholder="Add a note..."
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg p-2 text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none resize-none h-20"
                      />
                      <div className="flex justify-end mt-2">
                        <button
                          onClick={handleAddNote}
                          disabled={noteSaving || !noteInput.trim()}
                          className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
                        >
                          {noteSaving ? 'Saving...' : 'Add Note'}
                        </button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
              
              {/* Footer Actions */}
               <div className="p-4 border-t border-slate-700 flex gap-2 bg-slate-900">
                  <button
                    onClick={async () => {
                      if (!confirm('Delete this executive lead?')) return;
                      try {
                        await deleteLead(selectedLead.id);
                        setSelectedLead(null);
                        fetchLeads();
                      } catch (err) { console.error(err); }
                    }}
                    className="flex-1 px-3 py-2 bg-red-600/20 hover:bg-red-600/40 text-red-300 border border-red-600/50 rounded text-xs font-semibold transition-colors flex justify-center items-center gap-2">
                    <Trash2 className="h-3 w-3" /> Delete
                  </button>
                  <button
                    onClick={() => {
                         const text = `Company: ${selectedLead.company?.name}\nContext: ${selectedLead.context_dossier}`;
                         navigator.clipboard.writeText(text);
                    }}
                    className="flex-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 border border-slate-600 rounded text-xs font-semibold transition-colors flex justify-center items-center gap-2">
                    <Copy className="h-3 w-3" /> Copy
                  </button>
               </div>
            </div>
          ) : (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 text-center text-slate-400 h-full flex flex-col items-center justify-center">
               <div className="h-16 w-16 rounded-full bg-slate-700/50 flex items-center justify-center mb-4">
                 <Eye className="h-8 w-8 text-slate-500" />
               </div>
               <h3 className="text-lg font-bold text-white mb-2">Select a Lead</h3>
               <p className="text-sm max-w-xs mx-auto">
                 Click on any lead from the list to view their dossier, analysis, and activity history.
               </p>
            </div>
          )}
        </div>
      </div>

      {/* Full Dossier Modal */}
      <AnimatePresence>
        {showFullDossier && selectedLead && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div 
               initial={{ opacity: 0, scale: 0.95 }}
               animate={{ opacity: 1, scale: 1 }}
               exit={{ opacity: 0, scale: 0.95 }}
               className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl"
            >
              <div className="p-4 border-b border-slate-700 flex justify-between items-center">
                <h2 className="text-xl font-bold text-white">Strategy Dossier: {selectedLead.company?.name}</h2>
                <button onClick={() => setShowFullDossier(false)} className="text-slate-400 hover:text-white">
                  <X className="h-6 w-6" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto text-slate-300 space-y-6 leading-relaxed">
                 <div className="prose prose-invert max-w-none">
                   <h3 className="text-blue-400 font-bold text-sm uppercase mb-2">Challenger Insight</h3>
                   <p className="bg-blue-500/10 border-l-4 border-blue-500 p-4 rounded-r">
                     {selectedLead.challenger_insight || 'N/A'}
                   </p>
                   
                   <h3 className="text-green-400 font-bold text-sm uppercase mt-6 mb-2">Reframe Suggestion</h3>
                   <p className="bg-green-500/10 border-l-4 border-green-500 p-4 rounded-r">
                     {selectedLead.reframe_suggestion || 'N/A'}
                   </p>

                   <h3 className="text-slate-400 font-bold text-sm uppercase mt-6 mb-2">Full Context</h3>
                   <div className="whitespace-pre-wrap text-sm bg-slate-800 p-4 rounded border border-slate-700">
                     {selectedLead.context_dossier}
                   </div>
                 </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
