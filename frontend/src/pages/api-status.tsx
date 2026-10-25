import * as React from "react";
import {
  Activity,
  BookOpen,
  ExternalLink,
  FileJson2,
  RefreshCw,
  Server,
  ShieldCheck,
  Cpu,
} from "lucide-react";
import { PageWrapper, SectionWrapper } from "@/components/layout/page-wrapper";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchRuntimeSummary } from "@/lib/api";
import { joinApiUrl } from "@/lib/constants";
import { resolveApiBaseUrl } from "@/lib/env";
import type { RuntimeSummary, RuntimeProviderRow } from "@/types";

export function ApiStatusPage() {
  const [data, setData] = React.useState<RuntimeSummary | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);
  const activeApiUrl = resolveApiBaseUrl() || window.location.origin;

  const load = React.useCallback(async (isRefresh: boolean) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setErr(null);
    try {
      const d = await fetchRuntimeSummary();
      setData(d);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
      setData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  React.useEffect(() => {
    void load(false);
  }, [load]);

  const docsUrl = joinApiUrl("/docs");

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "working":
        return "Configured";
      case "disabled":
        return "Disabled by server policy";
      case "api_key_not_set":
        return "API Key Not Set";
      case "invalid_api_key":
        return "Invalid API Key";
      case "partial":
        return "Partial";
      case "unavailable":
        return "Unavailable";
      default:
        return status;
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "working":
      case "ok":
        return "success";
      case "partial":
      case "degraded":
        return "warning";
      case "invalid_api_key":
      case "error":
        return "destructive";
      case "api_key_not_set":
      case "unavailable":
      default:
        return "secondary";
    }
  };


  return (
    <PageWrapper>
      <SectionWrapper>
        <p className="section-kicker">Service overview</p>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-5 h-5 text-indigo-500" />
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
                Backend System Status
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 font-mono break-all">
              Base URL: <span className="font-semibold text-emerald-700 dark:text-emerald-400">{activeApiUrl}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void load(true)}
              disabled={loading || refreshing}
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href={docsUrl} target="_blank" rel="noopener noreferrer">
                <BookOpen className="w-3.5 h-3.5 mr-1" />
                OpenAPI Docs
                <ExternalLink className="w-3 h-3 ml-1 opacity-50" />
              </a>
            </Button>
          </div>
        </div>

        {err && (
          <GlassCard role="alert" padding="default" className="mb-6 border-red-500/50 bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300">
            <p className="text-sm font-medium">Failed to connect to backend ({activeApiUrl}): {err}</p>
          </GlassCard>
        )}

        {/* Overview Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <GlassCard padding="default">
            <GlassCardContent className="space-y-1">
              <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
                <span>API Status</span>
                <Server className="w-4 h-4" />
              </div>
              <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <Badge variant={getStatusBadgeVariant(data?.status ?? "")}>
                  {data?.status ?? (loading ? "Checking..." : "Offline")}
                </Badge>
              </div>
            </GlassCardContent>
          </GlassCard>

          <GlassCard padding="default">
            <GlassCardContent className="space-y-1">
              <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
                <span>Active Model</span>
                <Cpu className="w-4 h-4" />
              </div>
              <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                {data?.default_model ?? (loading ? "Checking…" : "Unavailable")}
              </div>
            </GlassCardContent>
          </GlassCard>

          <GlassCard padding="default">
            <GlassCardContent className="space-y-1">
              <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
                <span>Chunk Size</span>
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {data?.embedding_chunk_tokens ? `${data.embedding_chunk_tokens} tokens` : "Unavailable"}
              </div>
            </GlassCardContent>
          </GlassCard>

          <GlassCard padding="default">
            <GlassCardContent className="space-y-1">
              <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
                <span>Overlaps</span>
                <FileJson2 className="w-4 h-4" />
              </div>
              <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {data?.embedding_overlap_tokens !== undefined ? `${data.embedding_overlap_tokens} tokens` : "Unavailable"}
              </div>
            </GlassCardContent>
          </GlassCard>
        </div>

        {/* Configured Providers Grid */}
        {data?.providers_detail && data.providers_detail.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
              Configured Providers
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.providers_detail.map((prov: RuntimeProviderRow) => (
                <GlassCard key={prov.id} padding="default">
                  <GlassCardContent className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                        {prov.display_name}
                      </h3>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                        Status: <span>{getStatusLabel(prov.status)}</span>
                      </p>
                    </div>
                    <Badge variant={getStatusBadgeVariant(prov.status)}>
                      {getStatusLabel(prov.status)}
                    </Badge>

                  </GlassCardContent>
                </GlassCard>
              ))}
            </div>
          </div>
        )}
      </SectionWrapper>
    </PageWrapper>
  );
}
