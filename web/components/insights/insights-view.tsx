"use client";

import { ArrowDown, ArrowUp, BarChart3, RotateCw } from "lucide-react";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Label, Pie, PieChart, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CheckName, History, HistoryRow, Tier } from "@/lib/api";
import { FAILED_CHECK_LABEL, NEUTRAL_CHECKS, TIER_COLOR, TIERS } from "@/lib/tiers";
import { TierFilterControl, type TierFilter } from "../triage/pr-list";
import { TierDot } from "../triage/results-summary";

const ALL = "__all__";
const tierConfig = {
  "Review first": { label: "Review first", color: "var(--tier-review)" },
  "Needs info": { label: "Needs info", color: "var(--tier-info)" },
  "Likely low-effort": { label: "Likely low-effort", color: "var(--tier-low)" },
} satisfies ChartConfig;
const tierKey = (t: Tier) => t.replace(/[^a-z]/gi, "");
const histConfig = Object.fromEntries(
  TIERS.map((t) => [tierKey(t), { label: t, color: TIER_COLOR[t] }]),
) satisfies ChartConfig;
const failConfig = { count: { label: "PRs", color: "#71717a" } } satisfies ChartConfig;

type SortKey = "scored_at" | "repo" | "pr_number" | "title" | "author" | "final_score" | "tier";

export function InsightsView({
  history,
  loading,
  error,
  onRetry,
}: {
  history: History | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  const [repo, setRepo] = useState<string>(ALL);
  const [tier, setTier] = useState<TierFilter>("all");
  const rows = useMemo(() => history?.rows ?? [], [history]);
  const repos = useMemo(() => [...new Set(rows.map((r) => r.repo))].sort((a, b) => a.localeCompare(b)), [rows]);
  const byRepo = useMemo(() => (repo === ALL ? rows : rows.filter((r) => r.repo === repo)), [rows, repo]);
  const data = useMemo(() => (tier === "all" ? byRepo : byRepo.filter((r) => r.tier === tier)), [byRepo, tier]);
  const counts = useMemo(() => countTiers(byRepo), [byRepo]);

  if (loading && !history) return <InsightsSkeleton />;
  if (error)
    return (
      <Empty className="border border-border bg-card py-16">
        <EmptyHeader>
          <EmptyTitle>Couldn&apos;t load history</EmptyTitle>
          <EmptyDescription>{error}</EmptyDescription>
        </EmptyHeader>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw /> Try again
        </Button>
      </Empty>
    );
  if (!rows.length)
    return (
      <Empty className="border border-border bg-card py-16">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <BarChart3 />
          </EmptyMedia>
          <EmptyTitle>No history yet</EmptyTitle>
          <EmptyDescription>Triage a repo and every scored PR will show up here.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );

  const avg = data.length ? data.reduce((s, r) => s + r.final_score, 0) / data.length : 0;
  const lowPct = data.length ? (data.filter((r) => r.tier === "Likely low-effort").length / data.length) * 100 : 0;

  return (
    <div className="animate-in fade-in space-y-6 duration-300">
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={repo}
          onValueChange={(v) => setRepo((v as string) ?? ALL)}
          items={[{ value: ALL, label: "All repos" }, ...repos.map((r) => ({ value: r, label: r }))]}
        >
          <SelectTrigger className="h-9 min-w-56 bg-card font-mono text-[13px]" aria-label="Filter by repo">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All repos</SelectItem>
            {repos.map((r) => (
              <SelectItem key={r} value={r} className="font-mono text-[13px]">
                {r}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <TierFilterControl value={tier} onChange={setTier} counts={counts} total={byRepo.length} />
        <span className="ml-auto text-xs text-muted-foreground">
          {history?.source === "demo cache" ? "Showing cached demo runs · " : ""}Storage: {history?.storage_backend}
        </span>
      </div>

      <dl className="grid grid-cols-2 overflow-hidden rounded-lg border border-border bg-card sm:grid-cols-4">
        <Stat label="PRs scored" value={String(data.length)} />
        <Stat label="Runs" value={String(new Set(data.map((r) => r.run_id)).size)} />
        <Stat label="Average score" value={avg.toFixed(0)} />
        <Stat label="Likely low-effort" value={`${lowPct.toFixed(0)}%`} tier="Likely low-effort" />
      </dl>

      {data.length === 0 ? (
        <Empty className="border border-border bg-card py-12">
          <EmptyHeader>
            <EmptyTitle>No PRs match these filters</EmptyTitle>
            <EmptyDescription>Pick another repo or tier.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-5">
            <Panel title="Tier breakdown" className="lg:col-span-2">
              <TierDonut rows={data} />
            </Panel>
            <Panel title="Score distribution" className="lg:col-span-3">
              <ScoreHistogram rows={data} />
            </Panel>
          </div>
          <Panel
            title="Most common failed checks"
            subtitle="What contributors most often leave out. First-timers and new accounts aren't counted as failures."
          >
            <FailedChecks rows={data} />
          </Panel>
          <Panel title="Latest scored PRs" subtitle="The 20 most recent, click a header to sort" flush>
            <LatestTable rows={data} />
          </Panel>
        </>
      )}
    </div>
  );
}

function countTiers(rows: HistoryRow[]) {
  const c = { "Review first": 0, "Needs info": 0, "Likely low-effort": 0 } as Record<Tier, number>;
  rows.forEach((r) => {
    if (r.tier in c) c[r.tier] += 1;
  });
  return c;
}

function Stat({ label, value, tier }: { label: string; value: string; tier?: Tier }) {
  return (
    <div className="border-border px-4 py-3 not-last:border-r max-sm:nth-2:border-r-0 max-sm:nth-[-n+2]:border-b">
      <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {tier && <TierDot tier={tier} className="size-1.5" />}
        {label}
      </dt>
      <dd className="mt-1 font-mono text-2xl font-medium tabular-nums">{value}</dd>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
  className = "",
  flush = false,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  flush?: boolean;
}) {
  return (
    <section className={`overflow-hidden rounded-lg border border-border bg-card ${className}`}>
      <header className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium">{title}</h3>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </header>
      <div className={flush ? "" : "px-4 pb-4"}>{children}</div>
    </section>
  );
}

const axisTick = { fill: "var(--muted-foreground)", fontSize: 12, fontFamily: "var(--font-geist-mono)" };

function TierDonut({ rows }: { rows: HistoryRow[] }) {
  const counts = countTiers(rows);
  const data = TIERS.filter((t) => counts[t] > 0).map((t) => ({ tier: t, count: counts[t], fill: TIER_COLOR[t] }));
  return (
    <div className="flex items-center gap-6">
      <ChartContainer config={tierConfig} className="aspect-square h-52 shrink-0">
        <PieChart>
          <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel nameKey="tier" />} />
          <Pie data={data} dataKey="count" nameKey="tier" innerRadius={62} outerRadius={88} strokeWidth={2} stroke="var(--card)" isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.tier} fill={d.fill} />
            ))}
            <Label
              content={({ viewBox }) => {
                if (!viewBox || !("cx" in viewBox)) return null;
                return (
                  <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle" dominantBaseline="middle">
                    <tspan x={viewBox.cx} y={(viewBox.cy ?? 0) - 6} className="fill-zinc-900 font-mono text-2xl font-medium">
                      {rows.length}
                    </tspan>
                    <tspan x={viewBox.cx} y={(viewBox.cy ?? 0) + 16} className="fill-zinc-500 text-xs">
                      PRs
                    </tspan>
                  </text>
                );
              }}
            />
          </Pie>
        </PieChart>
      </ChartContainer>
      <ul className="space-y-2.5 text-sm">
        {TIERS.map((t) => (
          <li key={t} className="flex items-center gap-2">
            <TierDot tier={t} />
            <span className="text-zinc-700">{t}</span>
            <span className="ml-auto pl-4 font-mono text-muted-foreground tabular-nums">{counts[t]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScoreHistogram({ rows }: { rows: HistoryRow[] }) {
  const bins = Array.from({ length: 10 }, (_, i) => ({
    range: i === 9 ? "90–100" : `${i * 10}–${i * 10 + 9}`,
    ...Object.fromEntries(TIERS.map((t) => [tierKey(t), 0])),
  })) as Array<Record<string, number | string>>;
  rows.forEach((r) => {
    const i = Math.min(9, Math.max(0, Math.floor(r.final_score / 10)));
    (bins[i][tierKey(r.tier)] as number) += 1;
  });
  return (
    <ChartContainer config={histConfig} className="h-52 w-full">
      <BarChart data={bins} margin={{ left: -20, right: 4, top: 8 }} barCategoryGap={4}>
        <CartesianGrid vertical={false} stroke="var(--color-zinc-100)" />
        <XAxis dataKey="range" tickLine={false} axisLine={false} tick={axisTick} interval={0} fontSize={11} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={axisTick} width={40} />
        <ChartTooltip cursor={{ fill: "var(--color-zinc-100)" }} content={<ChartTooltipContent />} />
        {TIERS.map((t, i) => (
          <Bar
            key={t}
            dataKey={tierKey(t)}
            stackId="a"
            fill={TIER_COLOR[t]}
            radius={i === TIERS.length - 1 ? [3, 3, 0, 0] : 0}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    </ChartContainer>
  );
}

function FailedChecks({ rows }: { rows: HistoryRow[] }) {
  const counts = new Map<string, number>();
  rows.forEach((r) =>
    (r.failed_checks || "")
      .split(",")
      .filter((c) => c && !NEUTRAL_CHECKS.has(c as CheckName)) // contributor history is context, not a fail
      .forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1)),
  );
  const data = [...counts.entries()]
    .map(([check, count]) => ({ check: FAILED_CHECK_LABEL[check as CheckName] ?? check, count }))
    .sort((a, b) => b.count - a.count);
  if (!data.length) return <p className="py-6 text-sm text-muted-foreground">Every check passed for these PRs.</p>;
  return (
    <ChartContainer config={failConfig} className="w-full" style={{ height: data.length * 34 + 16 }}>
      <BarChart data={data} layout="vertical" margin={{ left: 0, right: 32, top: 4, bottom: 4 }} barCategoryGap={8}>
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis type="category" dataKey="check" tickLine={false} axisLine={false} width={170} tick={{ fill: "var(--color-zinc-700)", fontSize: 13 }} />
        <ChartTooltip cursor={{ fill: "var(--color-zinc-50)" }} content={<ChartTooltipContent hideLabel={false} />} />
        <Bar
          dataKey="count"
          fill="var(--color-zinc-400)"
          radius={[0, 3, 3, 0]}
          isAnimationActive={false}
          label={{ position: "right", fill: "var(--muted-foreground)", fontSize: 12, fontFamily: "var(--font-geist-mono)" }}
        />
      </BarChart>
    </ChartContainer>
  );
}

const COLUMNS: { key: SortKey; label: string; className?: string }[] = [
  { key: "scored_at", label: "Scored", className: "w-32" },
  { key: "repo", label: "Repo" },
  { key: "pr_number", label: "PR", className: "w-20" },
  { key: "title", label: "Title" },
  { key: "author", label: "Author" },
  { key: "final_score", label: "Score", className: "w-20 text-right" },
  { key: "tier", label: "Tier", className: "w-40" },
];

function LatestTable({ rows }: { rows: HistoryRow[] }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "scored_at", dir: -1 });
  const latest = useMemo(
    () => [...rows].sort((a, b) => (b.scored_at ?? "").localeCompare(a.scored_at ?? "")).slice(0, 20),
    [rows],
  );
  const sorted = useMemo(() => {
    const val = (r: HistoryRow) => (sort.key === "tier" ? TIERS.indexOf(r.tier) : (r[sort.key] ?? ""));
    return [...latest].sort((a, b) => {
      const x = val(a);
      const y = val(b);
      const cmp = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
      return cmp * sort.dir;
    });
  }, [latest, sort]);
  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: key === "final_score" || key === "scored_at" ? -1 : 1 }));

  return (
    <div className="overflow-x-auto border-t border-border">
      <Table className="text-[13px]">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {COLUMNS.map((c) => (
              <TableHead key={c.key} className={c.className} aria-sort={sort.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
                <button
                  onClick={() => toggle(c.key)}
                  className={`inline-flex items-center gap-1 rounded text-xs font-medium text-muted-foreground hover:text-zinc-900 focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:outline-none ${c.key === "final_score" ? "flex-row-reverse" : ""}`}
                >
                  {c.label}
                  {sort.key === c.key && (sort.dir === 1 ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
                </button>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((r) => (
            <TableRow key={`${r.run_id}-${r.repo}-${r.pr_number}`}>
              <TableCell className="font-mono text-xs text-muted-foreground">{formatDate(r.scored_at)}</TableCell>
              <TableCell className="max-w-44 truncate font-mono text-xs">{r.repo}</TableCell>
              <TableCell className="font-mono text-xs">
                <a href={r.url} target="_blank" rel="noreferrer" className="hover:underline">
                  #{r.pr_number}
                </a>
              </TableCell>
              <TableCell className="max-w-72 truncate" title={r.title}>
                {r.title}
              </TableCell>
              <TableCell className="max-w-32 truncate text-zinc-600">@{r.author}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{r.final_score}</TableCell>
              <TableCell>
                <span className="inline-flex items-center gap-1.5 text-zinc-700">
                  <TierDot tier={r.tier} className="size-1.5" />
                  {r.tier}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "cached";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
}

function InsightsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-3">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-9 w-96" />
      </div>
      <Skeleton className="h-20 w-full" />
      <div className="grid gap-4 lg:grid-cols-5">
        <Skeleton className="h-64 lg:col-span-2" />
        <Skeleton className="h-64 lg:col-span-3" />
      </div>
    </div>
  );
}
