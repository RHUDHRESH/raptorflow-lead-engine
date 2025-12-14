'use client';

import { useState } from 'react';
import { useMissionStore } from '@/lib/store';
import { 
  Settings, 
  Server, 
  Webhook, 
  FileText, 
  Save,
  CheckCircle2,
  AlertCircle,
  Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TextShimmer } from '@/components/ui/text-shimmer';
import { motion } from 'framer-motion';

export function SettingsPanel() {
  const { settings, updateSettings } = useMissionStore();
  const [localSettings, setLocalSettings] = useState(settings);
  const [saved, setSaved] = useState(false);
  const [testResults, setTestResults] = useState<{
    ollama: 'idle' | 'testing' | 'success' | 'error';
    n8n: 'idle' | 'testing' | 'success' | 'error';
  }>({
    ollama: 'idle',
    n8n: 'idle',
  });

  const handleSave = () => {
    updateSettings(localSettings);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const testOllamaConnection = async () => {
    setTestResults((prev) => ({ ...prev, ollama: 'testing' }));
    try {
      const response = await fetch(`${localSettings.ollamaUrl}/api/tags`, {
        method: 'GET',
      });
      if (response.ok) {
        const data = await response.json();
        const hasFastModel = data.models?.some((m: any) => m.name.includes('gemma3:1b'));
        const hasReasoningModel = data.models?.some((m: any) => m.name.includes('gemma3:4b'));
        if (hasFastModel && hasReasoningModel) {
          setTestResults((prev) => ({ ...prev, ollama: 'success' }));
        } else {
          setTestResults((prev) => ({ ...prev, ollama: 'error' }));
        }
      } else {
        setTestResults((prev) => ({ ...prev, ollama: 'error' }));
      }
    } catch (error) {
      setTestResults((prev) => ({ ...prev, ollama: 'error' }));
    }
  };

  const testN8nConnection = async () => {
    setTestResults((prev) => ({ ...prev, n8n: 'testing' }));
    try {
      const response = await fetch(localSettings.n8nWebhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test: true }),
      });
      if (response.ok || response.status === 405) {
        setTestResults((prev) => ({ ...prev, n8n: 'success' }));
      } else {
        setTestResults((prev) => ({ ...prev, n8n: 'error' }));
      }
    } catch (error) {
      setTestResults((prev) => ({ ...prev, n8n: 'error' }));
    }
  };

  const getStatusIcon = (status: 'idle' | 'testing' | 'success' | 'error') => {
    switch (status) {
      case 'testing':
        return <TextShimmer className="text-sm">Testing...</TextShimmer>;
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="max-w-4xl mx-auto p-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Settings className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold text-foreground">System Settings</h1>
          </div>
          <p className="text-muted-foreground">
            Configure your local-first AI infrastructure. All settings are stored locally.
          </p>
        </div>

        <div className="space-y-8">
          {/* Local Server Status */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-6 rounded-lg border border-border bg-card"
          >
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Server className="h-5 w-5" />
              Local Server Status
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded border border-border bg-background">
                <div>
                  <p className="font-medium text-foreground">Ollama Server</p>
                  <p className="text-sm text-muted-foreground">{settings.ollamaUrl}</p>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(testResults.ollama)}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={testOllamaConnection}
                    disabled={testResults.ollama === 'testing'}
                  >
                    Test Connection
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 rounded border border-border bg-background">
                <div>
                  <p className="font-medium text-foreground">Fast Model</p>
                  <p className="text-sm text-muted-foreground">{settings.fastModel}</p>
                </div>
                <span className="text-xs text-green-500 bg-green-500/10 px-2 py-1 rounded">
                  LOADED
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded border border-border bg-background">
                <div>
                  <p className="font-medium text-foreground">Reasoning Model</p>
                  <p className="text-sm text-muted-foreground">{settings.reasoningModel}</p>
                </div>
                <span className="text-xs text-green-500 bg-green-500/10 px-2 py-1 rounded">
                  LOADED
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded border border-border bg-background">
                <div>
                  <p className="font-medium text-foreground">Agent Engine</p>
                  <p className="text-sm text-muted-foreground">LangGraph</p>
                </div>
                <span className="text-xs text-blue-500 bg-blue-500/10 px-2 py-1 rounded">
                  IDLE
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded border border-border bg-background">
                <div>
                  <p className="font-medium text-foreground">Automation</p>
                  <p className="text-sm text-muted-foreground">n8n Workflow</p>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(testResults.n8n)}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={testN8nConnection}
                    disabled={testResults.n8n === 'testing'}
                  >
                    Test Connection
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Connection Settings */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="p-6 rounded-lg border border-border bg-card"
          >
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Webhook className="h-5 w-5" />
              Connection Settings
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Ollama Server URL
                </label>
                <input
                  type="text"
                  value={localSettings.ollamaUrl}
                  onChange={(e) =>
                    setLocalSettings({ ...localSettings, ollamaUrl: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="http://localhost:11434"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Default: http://localhost:11434
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  n8n Webhook URL
                </label>
                <input
                  type="text"
                  value={localSettings.n8nWebhookUrl}
                  onChange={(e) =>
                    setLocalSettings({ ...localSettings, n8nWebhookUrl: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="http://localhost:5678/webhook/my-sdr-mission"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Your n8n workflow webhook endpoint
                </p>
              </div>
            </div>
          </motion.div>

          {/* Model Configuration */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="p-6 rounded-lg border border-border bg-card"
          >
            <h2 className="text-xl font-semibold text-foreground mb-4">Model Configuration</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Fast Model (gemma3:1b)
                </label>
                <input
                  type="text"
                  value={localSettings.fastModel}
                  onChange={(e) =>
                    setLocalSettings({ ...localSettings, fastModel: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Reasoning Model (gemma3:4b)
                </label>
                <input
                  type="text"
                  value={localSettings.reasoningModel}
                  onChange={(e) =>
                    setLocalSettings({ ...localSettings, reasoningModel: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </motion.div>

          {/* ICP & Prompts */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="p-6 rounded-lg border border-border bg-card"
          >
            <h2 className="text-xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              ICP & Prompts
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Default Ideal Customer Profile (ICP)
                </label>
                <textarea
                  value={localSettings.icp}
                  onChange={(e) =>
                    setLocalSettings({ ...localSettings, icp: e.target.value })
                  }
                  rows={4}
                  className="w-full px-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  placeholder="Founder-led B2B SaaS companies with 1-20 employees..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  RaptorFlow Features (for Contextual Reports)
                </label>
                <textarea
                  value={localSettings.raptorFlowFeatures}
                  onChange={(e) =>
                    setLocalSettings({ ...localSettings, raptorFlowFeatures: e.target.value })
                  }
                  rows={8}
                  className="w-full px-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none font-mono text-sm"
                />
              </div>
            </div>
          </motion.div>

          {/* Info Box */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="p-4 rounded-lg border border-blue-500/20 bg-blue-500/10"
          >
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-foreground">
                <p className="font-medium mb-1">100% Local & Private</p>
                <p className="text-muted-foreground">
                  All data is stored locally in your browser. No data is sent to external servers
                  except for the web scraping operations you configure. Your Ollama server and n8n
                  workflow run entirely on your local machine.
                </p>
              </div>
            </div>
          </motion.div>

          {/* Save Button */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="flex justify-end"
          >
            <Button
              onClick={handleSave}
              size="lg"
              className="min-w-[120px]"
            >
              {saved ? (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Saved!
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Settings
                </>
              )}
            </Button>
          </motion.div>
        </div>
      </div>
    </div>
  );
}


