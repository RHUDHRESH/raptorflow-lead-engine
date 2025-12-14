'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  Activity,
  Download,
  FileText,
  Loader2,
  MoreHorizontal,
  Rocket,
  Settings,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

import { SystemStatus } from '@/components/system-status';
import { getApiBaseUrl, getLead, getLeadPdfExportUrl, getLeadsCsvExportUrl, getSystemHealth, launchMission, listLeads } from '@/lib/api';

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
  company_website?: string;
  score: number;
  score_bucket: string;
  role_type: string;
  contact?: {
    id?: number | null;
    name?: string | null;
    role?: string | null;
    email?: string | null;
    phone_numbers?: string[] | null;
  };
  circumstances?: {
    situation?: string | null;
    problem?: string | null;
    implication?: string | null;
    need_payoff?: string | null;
    key_pain?: string | null;
    pain_tags?: string[] | null;
  };
}

type LeadDetails = Awaited<ReturnType<typeof getLead>>;

function bucketBadgeVariant(bucket: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (bucket) {
    case 'red_hot':
      return 'destructive';
    case 'warm':
      return 'default';
    case 'nurture':
      return 'secondary';
    default:
      return 'outline';
  }
}

export function MissionConsole() {
  const [prompt, setPrompt] = useState('Find companies hiring marketing leaders in India with clear growth pain.');
  const [isRunning, setIsRunning] = useState(false);
  const [healthState, setHealthState] = useState<'ok' | 'issue' | 'checking'>('checking');
  const [showFlightCheck, setShowFlightCheck] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const [apiBase, setApiBase] = useState<string>(() => getApiBaseUrl());

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [latestImage, setLatestImage] = useState<string | null>(null);
  const [leads, setLeads] = useState<LeadPreview[]>([]);

  const [leadSheetOpen, setLeadSheetOpen] = useState(false);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [selectedLead, setSelectedLead] = useState<LeadDetails | null>(null);
  const [selectedLeadLoading, setSelectedLeadLoading] = useState(false);
  const [selectedLeadError, setSelectedLeadError] = useState<string | null>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);

  const missionTimeoutRef = useRef<number | null>(null);

  const addLog = (entry: Omit<LogEntry, 'id' | 'timestamp'>) => {
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        timestamp: new Date(),
        ...entry,
      },
    ]);
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      // Set immediately so SSE can connect even while health/leads are loading.
      setApiBase(getApiBaseUrl());

      try {
        const data = await getSystemHealth();
        const ok = data?.api === 'ok' && data?.database === 'ok' && data?.ollama?.status === 'ok';
        if (!cancelled) {
          setHealthState(ok ? 'ok' : 'issue');
          setApiBase(getApiBaseUrl());
        }
      } catch {
        if (!cancelled) {
          setHealthState('issue');
          setApiBase(getApiBaseUrl());
        }
      }

      try {
        const existing = await listLeads({ limit: 50, offset: 0 });
        if (!cancelled) {
          // listLeads may have discovered a better base URL; keep SSE aligned.
          setApiBase(getApiBaseUrl());
          setLeads(
            (existing || [])
              .filter((lead) => {
                const name = (lead.contact?.name || '').trim();
                const email = (lead.contact?.email || '').trim();
                const phones = lead.contact?.phone_numbers || [];
                return Boolean((email || (Array.isArray(phones) && phones.length > 0)) && (name || email));
              })
              .map((lead) => ({
                id: lead.id,
                company: lead.company?.name || 'Unknown',
                company_website: lead.company?.website,
                score: Number(lead.total_score ?? 0) || 0,
                score_bucket: lead.score_bucket,
                role_type: lead.role_type || 'unknown',
                contact: lead.contact
                  ? {
                      id: lead.contact.id,
                      name: lead.contact.name,
                      role: lead.contact.role,
                      email: lead.contact.email,
                      phone_numbers: lead.contact.phone_numbers,
                    }
                  : undefined,
                circumstances: {
                  situation: lead.situation,
                  problem: lead.problem,
                  implication: lead.implication,
                  need_payoff: lead.need_payoff,
                  key_pain: lead.key_pain,
                  pain_tags: lead.pain_tags,
                },
              }))
          );
        }
      } catch {
        // ignore
      }
    };

    init();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!apiBase) return;

    const eventSource = new EventSource(`${apiBase}/api/events`);

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);

        if (parsed.type === 'mission_log') {
          const logData = parsed.data;
          addLog({
            agent: logData.agent,
            message: logData.message,
            type: logData.type,
            image_url: logData.image_url,
          });

          if (logData.image_url) {
            setLatestImage(logData.image_url);
          }

          if (logData.agent === 'Mission Control' && (logData.type === 'success' || logData.type === 'error')) {
            setIsRunning(false);
            if (missionTimeoutRef.current) {
              window.clearTimeout(missionTimeoutRef.current);
              missionTimeoutRef.current = null;
            }
            if (logData.type === 'success') {
              toast.success('Mission completed');
            } else {
              toast.error('Mission failed');
            }
          }
        }

        if (parsed.type === 'lead_created') {
          const lead = parsed.data as LeadPreview;
          setLeads((prev) => {
            if (lead?.id && prev.some((p) => p.id === lead.id)) return prev;
            return [lead, ...prev];
          });
        }
      } catch {
        // ignore malformed SSE events
      }
    };

    eventSource.onerror = () => {
      // Keep UI alive; backend may restart.
    };

    return () => eventSource.close();
  }, [apiBase]);

  const exportCsv = () => {
    toast.success('Exporting CSV');
    window.open(getLeadsCsvExportUrl(), '_blank', 'noopener,noreferrer');
  };

  const downloadPdf = (leadId: number) => {
    toast.success('Generating PDF');
    window.open(getLeadPdfExportUrl(leadId), '_blank', 'noopener,noreferrer');
  };

  const openLead = async (leadId: number) => {
    setLeadSheetOpen(true);
    setSelectedLeadId(leadId);
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

  const runMission = async () => {
    if (!prompt.trim() || isRunning) return;

    setIsRunning(true);
    setLogs([]);
    setLeads([]);
    setLatestImage(null);
    toast.message('Mission started');

    if (missionTimeoutRef.current) {
      window.clearTimeout(missionTimeoutRef.current);
    }
    missionTimeoutRef.current = window.setTimeout(() => {
      setIsRunning(false);
      toast.error('Mission timed out');
      addLog({
        agent: 'Mission Control',
        message: 'Mission timed out (no completion event received).',
        type: 'error',
      });
    }, 180000);

    try {
      await launchMission(prompt);
    } catch (e) {
      setIsRunning(false);
      if (missionTimeoutRef.current) {
        window.clearTimeout(missionTimeoutRef.current);
        missionTimeoutRef.current = null;
      }
      toast.error('Failed to start mission');
      addLog({
        agent: 'Mission Control',
        message: e instanceof Error ? e.message : 'Failed to start mission',
        type: 'error',
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Rocket className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold">Mission Control</div>
              <div className="text-xs text-muted-foreground">Discover → classify → export</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={exportCsv}>
              <Download className="h-4 w-4 mr-2" /> Export CSV
            </Button>

            <Button
              variant={healthState === 'issue' ? 'destructive' : 'outline'}
              onClick={() => setShowFlightCheck(true)}
            >
              <Activity className="h-4 w-4 mr-2" /> Flight Check
            </Button>

            <Button variant="outline" onClick={() => setShowSettings((v) => !v)}>
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <SystemStatus isOpen={showFlightCheck} onClose={() => setShowFlightCheck(false)} />

      <div className="mx-auto max-w-6xl px-4 py-6 space-y-6">
        {showSettings && (
          <div className="rounded-lg border bg-card text-card-foreground p-4">
            <div className="text-sm font-semibold">Settings</div>
            <div className="mt-1 text-xs text-muted-foreground">UI is ready. Backend pipeline options will be exposed here next.</div>
          </div>
        )}

        <div className="rounded-lg border bg-card text-card-foreground p-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="text-sm font-semibold">Your Mission</div>
              <div className="text-xs text-muted-foreground">Describe the leads you want. We’ll generate and score them live.</div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => { setLogs([]); setLeads([]); setLatestImage(null); }}>
                Clear
              </Button>

              <Button onClick={runMission} disabled={!prompt.trim() || isRunning}>
                {isRunning ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Running
                  </>
                ) : (
                  <>
                    <Rocket className="h-4 w-4 mr-2" /> Go
                  </>
                )}
              </Button>
            </div>
          </div>

          <div className="mt-4">
            <Input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Marketing leaders hiring growth roles, India, B2B SaaS"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  runMission();
                }
              }}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="mt-4 rounded-lg border bg-card overflow-hidden">
            <div className="px-4 py-3 flex items-center justify-between">
              <div className="text-sm font-medium">Leads</div>
              <div className="text-xs text-muted-foreground">{leads.length} total</div>
            </div>
            <Separator />
            <Separator />
            <div className="p-2">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Company</TableHead>
                      <TableHead className="hidden md:table-cell">Person</TableHead>
                      <TableHead className="hidden lg:table-cell">Email</TableHead>
                      <TableHead className="hidden lg:table-cell">Phone</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead>Bucket</TableHead>
                      <TableHead className="w-[48px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leads.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-sm text-muted-foreground py-10 text-center">
                        {isRunning ? 'Searching and scoring… leads will appear here.' : 'Press Go to generate leads.'}
                      </TableCell>
                    </TableRow>
                    ) : (
                      leads.map((lead) => (
                        <TableRow key={lead.id} className="cursor-pointer" onClick={() => openLead(lead.id)}>
                          <TableCell className="font-medium">
                            <div>{lead.company}</div>
                            {lead.company_website ? (
                              <div className="text-xs text-muted-foreground truncate max-w-[260px]">{lead.company_website}</div>
                            ) : null}
                          </TableCell>
                          <TableCell className="hidden md:table-cell">
                            <div className="text-sm">{lead.contact?.name || '—'}</div>
                            <div className="text-xs text-muted-foreground">{lead.contact?.role || lead.role_type || '—'}</div>
                          </TableCell>
                          <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                            {lead.contact?.email || '—'}
                          </TableCell>
                          <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                            {(lead.contact?.phone_numbers && lead.contact.phone_numbers.length > 0
                              ? lead.contact.phone_numbers.join(', ')
                              : '—')}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="text-sm font-medium">{Number(lead.score ?? 0).toFixed(0)}</div>
                          </TableCell>
                          <TableCell>
                            <Badge variant={bucketBadgeVariant(lead.score_bucket)}>{lead.score_bucket}</Badge>
                          </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openLead(lead.id)}>
                                View details
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => downloadPdf(lead.id)}>
                                Download PDF
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={exportCsv}>
                                Export CSV
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="rounded-lg border bg-card text-card-foreground">
            <div className="p-4">
              <div className="text-sm font-semibold">Activity</div>
              <div className="text-xs text-muted-foreground">Live logs + vision snapshot</div>
            </div>
            <Separator />
            <div className="p-4 space-y-4">
              <div className="rounded-md border bg-background">
                <ScrollArea className="h-[260px]">
                  <div className="p-3 space-y-2 text-xs">
                    {logs.length === 0 ? (
                      <div className="text-muted-foreground">No logs yet.</div>
                    ) : (
                      logs.map((log) => (
                        <div key={log.id} className="flex gap-2">
                          <div className="text-muted-foreground whitespace-nowrap">
                            {log.timestamp.toLocaleTimeString().split(' ')[0]}
                          </div>
                          <div className="flex-1">
                            <span className="font-medium">{log.agent}:</span> {log.message}
                          </div>
                        </div>
                      ))
                    )}
                    <div ref={logsEndRef} />
                  </div>
                </ScrollArea>
              </div>

              <div className="rounded-md border bg-background overflow-hidden">
                <div className="px-3 py-2 text-xs text-muted-foreground">Vision</div>
                <Separator />
                <div className="h-[160px] flex items-center justify-center bg-muted/20">
                  {latestImage ? (
                    <img src={latestImage} alt="Vision" className="max-h-full max-w-full object-contain" />
                  ) : (
                    <div className="text-xs text-muted-foreground">No vision snapshot</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Sheet open={leadSheetOpen} onOpenChange={setLeadSheetOpen}>
        <SheetContent className="sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Lead Details</SheetTitle>
            <SheetDescription>
              {selectedLeadId ? `Lead #${selectedLeadId}` : 'Select a lead from the table'}
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-4">
            {selectedLeadLoading && (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            )}

            {selectedLeadError && (
              <div className="text-sm text-destructive">{selectedLeadError}</div>
            )}

            {selectedLead && (
              <>
                <div>
                  <div className="text-lg font-semibold">{selectedLead.company?.name || 'Unknown'}</div>
                  <div className="text-sm text-muted-foreground">Score: {Number(selectedLead.total_score ?? 0).toFixed(0)} ({selectedLead.score_bucket})</div>
                </div>

                <Separator />

                <div className="space-y-1 text-sm">
                  <div>
                    <span className="text-muted-foreground">Website:</span>{' '}
                    {selectedLead.company?.website ? (
                      <a className="underline" href={selectedLead.company.website} target="_blank" rel="noreferrer">
                        {selectedLead.company.website}
                      </a>
                    ) : (
                      '—'
                    )}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Contact:</span> {selectedLead.contact?.name || '—'}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Email:</span> {selectedLead.contact?.email || '—'}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Phone(s):</span>{' '}
                    {(selectedLead.contact?.phone_numbers || []).join(', ') || '—'}
                  </div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground">Circumstances</div>
                  <div className="text-sm">
                    {selectedLead.key_pain || selectedLead.problem || selectedLead.situation || '—'}
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <Button variant="outline" onClick={() => downloadPdf(selectedLead.id)}>
                    <FileText className="h-4 w-4 mr-2" /> PDF
                  </Button>
                  <Button variant="outline" onClick={exportCsv}>
                    <Download className="h-4 w-4 mr-2" /> CSV
                  </Button>
                </div>
              </>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
