"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Users, DollarSign, Target, Clock, Building2 } from "lucide-react";

interface AdvancedSearchProps {
  onSearch: (filters: any) => void;
  loading: boolean;
}

export function AdvancedSearch({ onSearch, loading }: AdvancedSearchProps) {
  const [filters, setFilters] = useState({
    // Basic filters
    score_min: 80, // Default to high-value leads only
    score_max: 150,
    status: "",
    score_bucket: "",

    // Executive filters
    decision_making_level: "",
    budget_authority: "",
    target_priority: "",
    urgency_level: "",
    role_type: "",
    company_size_estimate: "",

    // Text search
    company_name_contains: "",
    economic_buyer_guess: "",

    // Scoring thresholds
    executive_level_min: 15,
    budget_potential_min: 10,

    // Sorting
    sort_by: "total_score",
    sort_desc: true
  });

  const handleSearch = () => {
    onSearch(filters);
  };

  const resetFilters = () => {
    setFilters({
      score_min: 80,
      score_max: 150,
      status: "",
      score_bucket: "",
      decision_making_level: "",
      budget_authority: "",
      target_priority: "",
      urgency_level: "",
      role_type: "",
      company_size_estimate: "",
      company_name_contains: "",
      economic_buyer_guess: "",
      executive_level_min: 15,
      budget_potential_min: 10,
      sort_by: "total_score",
      sort_desc: true
    });
  };

  const getPriorityBadge = (score: number) => {
    if (score >= 100) return <Badge variant="destructive">Strategic Gold</Badge>;
    if (score >= 85) return <Badge variant="secondary">High Value</Badge>;
    return <Badge variant="outline">Standard</Badge>;
  };

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Search className="h-5 w-5" />
          Executive Lead Search
          <span className="text-sm text-slate-400 font-normal">
            Target C-level decision makers with budget authority
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Company Size Targeting - NEW */}
        <div className="space-y-2">
          <Label className="text-slate-300">Company Size Requirements</Label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              { label: "5+ People", value: "5_plus" },
              { label: "10+ People", value: "10_plus" },
              { label: "20+ People", value: "20_plus" },
              { label: "50+ People", value: "50_plus" },
              { label: "100+ People", value: "100_plus" },
              { label: "Enterprise", value: "enterprise" },
              { label: "Any Size", value: "any_size" },
              { label: "Reject <5", value: "no_micro" }
            ].map(({ label, value }) => (
              <Button
                key={value}
                variant={filters.company_size_estimate === value ? "default" : "outline"}
                size="sm"
                onClick={() => setFilters(prev => ({ ...prev, company_size_estimate: value }))}
              >
                {label}
              </Button>
            ))}
          </div>
        </div>

        {/* Priority Preset */}
        <div className="flex gap-3 items-center flex-wrap">
          <Label className="text-slate-300">Executive Presets:</Label>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setFilters(prev => ({
              ...prev,
              decision_making_level: "founder_ceo",
              budget_authority: "high_yes",
              executive_level_min: 25
            }))}
          >
            👑 CEO/Founder Only
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setFilters(prev => ({
              ...prev,
              decision_making_level: "c_level",
              budget_authority: "high_yes",
              target_priority: "strategic_gold",
              urgency_level: "immediate_crisis"
            }))}
          >
            💎 Strategic Gold
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setFilters(prev => ({
              ...prev,
              urgency_level: "immediate_crisis",
              budget_potential_min: 15,
              company_size_estimate: "20_plus"
            }))}
          >
            🔥 In Crisis (Big Co)
          </Button>
        </div>

        {/* Executive Level Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label className="text-slate-300 flex items-center gap-1">
              <Users className="h-4 w-4" />
              Decision Level
            </Label>
            <Select
              value={filters.decision_making_level}
              onValueChange={(value) => setFilters(prev => ({ ...prev, decision_making_level: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Any level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="founder_ceo">Founder/CEO</SelectItem>
                <SelectItem value="c_level">C-Level</SelectItem>
                <SelectItem value="vp_director">VP/Director</SelectItem>
                <SelectItem value="manager">Manager</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300 flex items-center gap-1">
              <DollarSign className="h-4 w-4" />
              Budget Authority
            </Label>
            <Select
              value={filters.budget_authority}
              onValueChange={(value) => setFilters(prev => ({ ...prev, budget_authority: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Any budget" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="high_yes">High Authority</SelectItem>
                <SelectItem value="medium_maybe">Medium Authority</SelectItem>
                <SelectItem value="low_no">Limited Budget</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300 flex items-center gap-1">
              <Target className="h-4 w-4" />
              Target Priority
            </Label>
            <Select
              value={filters.target_priority}
              onValueChange={(value) => setFilters(prev => ({ ...prev, target_priority: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Any priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="strategic_gold">Strategic Gold</SelectItem>
                <SelectItem value="high_value">High Value</SelectItem>
                <SelectItem value="medium_potential">Medium Potential</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300 flex items-center gap-1">
              <Clock className="h-4 w-4" />
              Urgency Level
            </Label>
            <Select
              value={filters.urgency_level}
              onValueChange={(value) => setFilters(prev => ({ ...prev, urgency_level: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Any urgency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="immediate_crisis">Immediate Crisis</SelectItem>
                <SelectItem value="quarterly_priority">Quarterly Priority</SelectItem>
                <SelectItem value="future_plan">Future Plan</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Text Search */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label className="text-slate-300 flex items-center gap-1">
              <Building2 className="h-4 w-4" />
              Company Name
            </Label>
            <Input
              placeholder="e.g., Acme Corp"
              value={filters.company_name_contains}
              onChange={(e) => setFilters(prev => ({ ...prev, company_name_contains: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Economic Buyer</Label>
            <Select
              value={filters.economic_buyer_guess}
              onValueChange={(value) => setFilters(prev => ({ ...prev, economic_buyer_guess: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Any buyer" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="founder">Founder</SelectItem>
                <SelectItem value="ceo">CEO</SelectItem>
                <SelectItem value="cmo">CMO</SelectItem>
                <SelectItem value="cto">CTO</SelectItem>
                <SelectItem value="vp">VP</SelectItem>
                <SelectItem value="director">Director</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Score Thresholds */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label className="text-slate-300">Min Executive Level (0-30)</Label>
            <Input
              type="number"
              min="0"
              max="30"
              value={filters.executive_level_min}
              onChange={(e) => setFilters(prev => ({ ...prev, executive_level_min: parseInt(e.target.value) || 0 }))}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Min Budget Potential (0-20)</Label>
            <Input
              type="number"
              min="0"
              max="20"
              value={filters.budget_potential_min}
              onChange={(e) => setFilters(prev => ({ ...prev, budget_potential_min: parseInt(e.target.value) || 0 }))}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Min Total Score (0-150)</Label>
            <Input
              type="number"
              min="0"
              max="150"
              value={filters.score_min}
              onChange={(e) => setFilters(prev => ({ ...prev, score_min: parseInt(e.target.value) || 0 }))}
            />
          </div>
        </div>

        {/* Sort Options */}
        <div className="flex items-center gap-4 p-4 bg-slate-700/50 rounded-lg">
          <Label className="text-slate-300">Sort by:</Label>
          <Select
            value={filters.sort_by}
            onValueChange={(value) => setFilters(prev => ({ ...prev, sort_by: value }))}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="total_score">Total Score</SelectItem>
              <SelectItem value="score_executive_level">Executive Level</SelectItem>
              <SelectItem value="score_budget_potential">Budget Potential</SelectItem>
              <SelectItem value="created_at">Date Created</SelectItem>
              <SelectItem value="company_name">Company Name</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="sort_desc"
              checked={filters.sort_desc}
              onCheckedChange={(checked) => setFilters(prev => ({ ...prev, sort_desc: checked }))}
            />
            <Label htmlFor="sort_desc" className="text-slate-300">Descending</Label>
          </div>

          <div className="ml-auto flex gap-2">
            <Button variant="outline" onClick={resetFilters}>
              Reset
            </Button>
            <Button onClick={handleSearch} disabled={loading}>
              {loading ? "Searching..." : "Search Executive Leads"}
            </Button>
          </div>
        </div>

        {/* Search Preset Info */}
        <div className="text-xs text-slate-400">
          <p><strong>Note:</strong> This search focuses on high-value executive prospects. Average lead quality: CEO/Founder with marketing pain and budget authority. NOT individual contributors or entry-level roles.</p>
        </div>
      </CardContent>
    </Card>
  );
}
