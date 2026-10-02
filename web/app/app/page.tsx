"use client";

import { GitPullRequest, Inbox } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePersistentFlag } from "@/lib/use-persistent-flag";
import { toast } from "sonner";
import { Footer } from "@/components/footer";
import { HowItWorks } from "@/components/how-it-works";
import { InsightsView } from "@/components/insights/insights-view";
import { Navbar } from "@/components/navbar";
import { PRDrawer } from "@/components/triage/pr-drawer";
import { PRList, TierFilterControl, type TierFilter } from "@/components/triage/pr-list";
import { ProgressPanel } from "@/components/triage/progress-panel";
import { RepoForm } from "@/components/triage/repo-form";
import { ResultsSummary } from "@/components/triage/results-summary";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import {
  getDemoRepos,
  getHealth,
  getHistory,
  triage,
  type Health,
  type History,
  type PR,
  type Tier,
  type TriageResult,
} from "@/lib/api";

type Status = "idle" | "running" | "done" | "error";
const OFFLINE_KEY = "pr-lifeguard:offline-demo";

export default function TriageApp() {
  const [tab, setTab] = useState("triage");
  const [offline, setOffline] = usePersistentFlag(OFFLINE_KEY, true);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [cachedKeys, setCachedKeys] = useState<Set<string>>(new Set());

  const [repo, setRepo] = useState("firstcontributions/first-contributions");
  const [limit, setLimit] = useState(12);
  const [status, setStatus] = useState<Status>("idle");
  const [progress, setProgress] = useState({ message: "Starting…", fraction: 0 });
  const [result, setResult] = useState<TriageResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TierFilter>("all");
  const [openPR, setOpenPR] = useState<PR | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const [history, setHistory] = useState<History | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const refreshMeta = useCallback(() => {
    getHealth()
      .then((h) => {
        setHealth(h);
        setHealthError(false);
      })
      .catch(() => setHealthError(true));
    getDemoRepos()
      .then((d) => setCachedKeys(new Set(d.repos.map((r) => r.key))))
      .catch(() => {});
  }, []);

  const loadHistory = useCallback(() => {
    setHistoryLoading(true);
    getHistory()
      .then((h) => {
        setHistory(h);
        setHistoryError(null);
      })
      .catch((e: Error) => setHistoryError(e.message))
      .finally(() => setHistoryLoading(false));
  }, []);

  useEffect(() => {
    refreshMeta();
    // Storage is decided in the background on the API side; refresh once it settles.
    const t = setTimeout(refreshMeta, 4000);
    return () => clearTimeout(t);
  }, [refreshMeta]);

  const changeTab = (v: string) => {
    setTab(v);
    if (v === "insights") loadHistory();
  };

  const changeOffline = (v: boolean) => {
    setOffline(v);
    toast(v ? "Offline demo on" : "Offline demo off", {
      description: v ? "Cached repos replay instantly, no network needed." : "Triage runs live against GitHub and the model.",
    });
  };

  const run = async (repoOverride?: string, forceOffline?: boolean) => {
    const target = (repoOverride ?? repo).trim();
    if (!target) return;
    const useOffline = forceOffline ?? offline;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setStatus("running");
    setError(null);
    setFilter("all");
    setProgress({ message: useOffline ? "Loading cached run…" : "Starting…", fraction: 0.02 });
    try {
      const res = await triage(
        { repo: target, limit, offline_demo: useOffline },
        { onProgress: (message, fraction) => setProgress({ message, fraction }), signal: ctrl.signal },
      );
      if (ctrl.signal.aborted) return;
      setResult(res);
      setStatus("done");
      if (!useOffline) refreshMeta();
      setHistory(null);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      const message = (e as Error).message || "Something went wrong. Try again.";
      setError(message);
      setStatus("error");
      toast.error("Triage didn't finish", { description: "Details are shown above the results." });
    }
  };

  const prs = useMemo(() => [...(result?.prs ?? [])].sort((a, b) => b.final_score - a.final_score), [result]);
  const counts = useMemo(() => {
    const c = { "Review first": 0, "Needs info": 0, "Likely low-effort": 0 } as Record<Tier, number>;
    prs.forEach((p) => (c[p.tier] = (c[p.tier] ?? 0) + 1));
    return c;
  }, [prs]);
  const shown = filter === "all" ? prs : prs.filter((p) => p.tier === filter);
  const targetKey = repo.trim().replace(/^(https?:\/\/)?(www\.)?github\.com\//i, "").replace(/\.git$|\/$/g, "").toLowerCase();
  const canRetryOffline = !offline && cachedKeys.has(targetKey);

  return (
    <Tabs value={tab} onValueChange={(v) => changeTab(v as string)} className="flex min-h-screen flex-col gap-0">
      <Navbar health={health} healthError={healthError} offline={offline} onOfflineChange={changeOffline} />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <TabsContent value="triage" className="space-y-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Triage open pull requests</h1>
            <p className="text-sm text-muted-foreground">
              Ranked by effort, not by whether AI was used. Every score comes with its reasons and a kind draft reply.
            </p>
          </div>

          <RepoForm
            repo={repo}
            onRepoChange={setRepo}
            limit={limit}
            onLimitChange={setLimit}
            onSubmit={(r) => run(r)}
            busy={status === "running"}
            cachedKeys={cachedKeys}
            offline={offline}
          />

          {status === "running" && <ProgressPanel message={progress.message} fraction={progress.fraction} />}

          {status === "error" && error && (
            <div role="alert" className="animate-in fade-in rounded-lg border border-border border-l-2 border-l-primary bg-card px-4 py-3 duration-300">
              <p className="text-sm font-medium">Triage didn&apos;t finish</p>
              <p className="mt-0.5 text-sm text-muted-foreground">{error}</p>
              {canRetryOffline && (
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-3"
                  onClick={() => {
                    changeOffline(true);
                    run(undefined, true);
                  }}
                >
                  Use the cached run instead
                </Button>
              )}
              {offline && /^[\w.-]+\/[\w.-]+$/.test(targetKey) && !cachedKeys.has(targetKey) && !healthError && (
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-3"
                  onClick={() => {
                    changeOffline(false);
                    run(undefined, false);
                  }}
                >
                  Run it live instead
                </Button>
              )}
            </div>
          )}

          {status !== "running" && result && (
            <div className="space-y-5">
              <ResultsSummary result={result} counts={counts} />
              {prs.length === 0 ? (
                <Empty className="border border-border bg-card py-14">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <GitPullRequest />
                    </EmptyMedia>
                    <EmptyTitle>No open pull requests</EmptyTitle>
                    <EmptyDescription>{result.repo} has nothing waiting for review right now.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <TierFilterControl value={filter} onChange={setFilter} counts={counts} total={prs.length} />
                    <span className="text-xs text-muted-foreground">Sorted by effort score · click a PR for details</span>
                  </div>
                  {shown.length ? (
                    <PRList prs={shown} onOpen={setOpenPR} />
                  ) : (
                    <Empty className="border border-border bg-card py-12">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <Inbox />
                        </EmptyMedia>
                        <EmptyTitle>Nothing in “{filter}”</EmptyTitle>
                        <EmptyDescription>No PRs in this repo landed in that tier.</EmptyDescription>
                      </EmptyHeader>
                      <Button variant="outline" size="sm" onClick={() => setFilter("all")}>
                        Show all {prs.length}
                      </Button>
                    </Empty>
                  )}
                </>
              )}
            </div>
          )}

          {status !== "running" && !result && <HowItWorks />}
        </TabsContent>

        <TabsContent value="insights" className="space-y-6">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Insights</h1>
            <p className="text-sm text-muted-foreground">Trends across every saved run: tiers, scores and what contributors keep missing.</p>
          </div>
          <InsightsView history={history} loading={historyLoading} error={historyError} onRetry={loadHistory} />
        </TabsContent>
      </main>

      <Footer />
      <PRDrawer pr={openPR} onClose={() => setOpenPR(null)} />
    </Tabs>
  );
}
