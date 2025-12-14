'use client';

import { useState } from 'react';
import { useMissionStore, type Lead } from '@/lib/store';
import { 
  FileText, 
  Mail, 
  Phone, 
  Globe, 
  User, 
  Building2, 
  Calendar,
  Trash2,
  Copy,
  CheckCircle2,
  Search
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

export function DossierPanel() {
  const { leads, deleteLead } = useMissionStore();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(
    leads.length > 0 ? leads[0] : null
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const filteredLeads = leads.filter((lead) => {
    const query = searchQuery.toLowerCase();
    return (
      lead.name.toLowerCase().includes(query) ||
      lead.company.toLowerCase().includes(query) ||
      lead.email?.toLowerCase().includes(query) ||
      lead.title.toLowerCase().includes(query)
    );
  });

  const handleCopy = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flex h-full bg-background">
      {/* Lead List Sidebar */}
      <div className="w-80 border-r border-border bg-card flex flex-col">
        <div className="p-6 border-b border-border">
          <h2 className="text-xl font-bold text-foreground mb-4">Lead Dossiers</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search leads..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {filteredLeads.length} lead{filteredLeads.length !== 1 ? 's' : ''} found
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {filteredLeads.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6">
              <FileText className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No leads yet</h3>
              <p className="text-muted-foreground text-sm">
                Launch a mission from Mission Control to generate leads.
              </p>
            </div>
          ) : (
            <div className="p-2 space-y-2">
              <AnimatePresence>
                {filteredLeads.map((lead) => (
                  <motion.div
                    key={lead.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    onClick={() => setSelectedLead(lead)}
                    className={cn(
                      'p-4 rounded-lg border cursor-pointer transition-all',
                      selectedLead?.id === lead.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border bg-background hover:bg-accent'
                    )}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h3 className="font-semibold text-foreground">{lead.name}</h3>
                        <p className="text-sm text-muted-foreground">{lead.title}</p>
                      </div>
                    </div>
                    <p className="text-sm font-medium text-foreground mb-1">
                      {lead.company}
                    </p>
                    {lead.email && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Mail className="h-3 w-3" />
                        <span className="truncate">{lead.email}</span>
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Dossier View */}
      <div className="flex-1 overflow-y-auto">
        {selectedLead ? (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="p-8 max-w-4xl mx-auto"
          >
            <div className="mb-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h1 className="text-3xl font-bold text-foreground mb-2">
                    {selectedLead.name}
                  </h1>
                  <p className="text-lg text-muted-foreground">{selectedLead.title}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteLead(selectedLead.id)}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-lg border border-border bg-card">
                  <div className="flex items-center gap-2 mb-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-muted-foreground">Company</span>
                  </div>
                  <p className="text-foreground font-semibold">{selectedLead.company}</p>
                </div>

                <div className="p-4 rounded-lg border border-border bg-card">
                  <div className="flex items-center gap-2 mb-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-muted-foreground">Added</span>
                  </div>
                  <p className="text-foreground font-semibold">
                    {formatDate(selectedLead.createdAt)}
                  </p>
                </div>

                {selectedLead.email && (
                  <div className="p-4 rounded-lg border border-border bg-card">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium text-muted-foreground">Email</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(selectedLead.email!, 'email')}
                        className="h-6 w-6 p-0"
                      >
                        {copiedField === 'email' ? (
                          <CheckCircle2 className="h-3 w-3 text-green-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <a
                      href={`mailto:${selectedLead.email}`}
                      className="text-foreground font-semibold hover:text-primary break-all"
                    >
                      {selectedLead.email}
                    </a>
                  </div>
                )}

                {selectedLead.phone && (
                  <div className="p-4 rounded-lg border border-border bg-card">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium text-muted-foreground">Phone</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(selectedLead.phone!, 'phone')}
                        className="h-6 w-6 p-0"
                      >
                        {copiedField === 'phone' ? (
                          <CheckCircle2 className="h-3 w-3 text-green-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <a
                      href={`tel:${selectedLead.phone}`}
                      className="text-foreground font-semibold hover:text-primary"
                    >
                      {selectedLead.phone}
                    </a>
                  </div>
                )}

                {selectedLead.url && (
                  <div className="p-4 rounded-lg border border-border bg-card">
                    <div className="flex items-center gap-2 mb-2">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium text-muted-foreground">Source URL</span>
                    </div>
                    <a
                      href={selectedLead.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground font-semibold hover:text-primary break-all text-sm"
                    >
                      {selectedLead.url}
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Contextual Relevance Report */}
            <div className="border-t border-border pt-6">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-5 w-5 text-primary" />
                <h2 className="text-2xl font-bold text-foreground">
                  Contextual Relevance Report
                </h2>
                <span className="text-xs text-muted-foreground bg-primary/10 text-primary px-2 py-1 rounded">
                  Generated by gemma3:4b
                </span>
              </div>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div className="whitespace-pre-wrap text-foreground leading-relaxed">
                  {selectedLead.report || 'No report available.'}
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <FileText className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-xl font-semibold mb-2">Select a lead</h3>
            <p className="text-muted-foreground max-w-md">
              Choose a lead from the sidebar to view their dossier and contextual relevance report.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}


