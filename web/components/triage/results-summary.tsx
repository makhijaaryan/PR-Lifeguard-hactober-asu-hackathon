import { ExternalLink } from "lucide-react";
import type { Tier, TriageResult } from "@/lib/api";
import { TIER_COLOR, TIERS } from "@/lib/tiers";

export function TierDot({ tier, className = "size-2" }: { tier: Tier; className?: string }) {
  return <span className={`inline-block shrink-0 rounded-full ${className}`} style={{ background: TIER_COLOR[tier] }} />;
}

export function ResultsSummary({ result, counts }: { result: TriageResult; counts: Record<Tier, number> }) {
  const total = result.prs.length;
  return (
    <section className="animate-in fade-in slide-in-from-bottom-1 duration-300">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <a
          href={`https://github.com/${result.repo}`}
          target="_blank"
          rel="noreferrer"
          className="group inline-flex items-center gap-1.5 text-lg font-semibold tracking-tight hover:underline"
        >
          {result.repo}
          <ExternalLink className="size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </a>
        <span className="font-mono text-xs text-muted-foreground">
          {result.offline_demo ? "offline demo · " : ""}
          {result.model_used} · run {result.run_id}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-2 overflow-hidden rounded-lg border border-border bg-card sm:grid-cols-4">
        <Stat label="Total PRs" value={total} />
        {TIERS.map((t) => (
          <Stat key={t} label={t} value={counts[t]} tier={t} />
        ))}
      </dl>

      <div className="mt-3 flex h-1.5 gap-0.5 overflow-hidden rounded-full" aria-label="Tier breakdown">
        {total === 0 ? (
          <div className="flex-1 bg-zinc-200" />
        ) : (
          TIERS.filter((t) => counts[t] > 0).map((t) => (
            <div
              key={t}
              className="h-full transition-[flex-grow] duration-500"
              style={{ flexGrow: counts[t], background: TIER_COLOR[t] }}
              title={`${t}: ${counts[t]}`}
            />
          ))
        )}
      </div>
    </section>
  );
}

function Stat({ label, value, tier }: { label: string; value: number; tier?: Tier }) {
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
