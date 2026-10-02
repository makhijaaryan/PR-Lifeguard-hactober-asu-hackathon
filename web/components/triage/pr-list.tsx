"use client";

import { ChevronRight } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { CheckName, PR, Tier } from "@/lib/api";
import { CHECK_ORDER, checkLabel, NEUTRAL_CHECKS, TIER_COLOR, TIERS } from "@/lib/tiers";
import { cn } from "@/lib/utils";
import { TierDot } from "./results-summary";

export type TierFilter = "all" | Tier;

export function TierFilterControl({
  value,
  onChange,
  counts,
  total,
}: {
  value: TierFilter;
  onChange: (v: TierFilter) => void;
  counts: Record<Tier, number>;
  total: number;
}) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as TierFilter)}>
      <TabsList className="h-9 max-w-full overflow-x-auto bg-zinc-100 p-[3px]" aria-label="Filter by tier">
        <FilterItem value="all" label="All" count={total} />
        {TIERS.map((t) => (
          <FilterItem key={t} value={t} label={t} count={counts[t]} tier={t} />
        ))}
      </TabsList>
    </Tabs>
  );
}

function FilterItem({ value, label, count, tier }: { value: string; label: string; count: number; tier?: Tier }) {
  return (
    <TabsTrigger
      value={value}
      className="h-full gap-1.5 px-3 text-[13px] data-active:shadow-sm focus-visible:ring-primary/20"
    >
      {tier && <TierDot tier={tier} className="size-1.5" />}
      {label}
      <span className="font-mono text-xs text-muted-foreground tabular-nums">{count}</span>
    </TabsTrigger>
  );
}

export function PRList({ prs, onOpen }: { prs: PR[]; onOpen: (pr: PR) => void }) {
  return (
    <ul className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
      {prs.map((pr, i) => (
        <PRRow key={pr.number} pr={pr} onOpen={onOpen} index={i} />
      ))}
    </ul>
  );
}

function PRRow({ pr, onOpen, index }: { pr: PR; onOpen: (pr: PR) => void; index: number }) {
  const failed = CHECK_ORDER.filter((n) => pr.rule_flags[n] && !pr.rule_flags[n].passed);
  const passed = CHECK_ORDER.length - failed.length;
  // Real faults first, then neutral context tags.
  const ordered = [...failed.filter((n) => !NEUTRAL_CHECKS.has(n)), ...failed.filter((n) => NEUTRAL_CHECKS.has(n))];
  return (
    <li
      className="animate-in fade-in slide-in-from-bottom-1 border-b border-border fill-mode-both last:border-b-0"
      style={{ animationDelay: `${Math.min(index, 12) * 25}ms`, animationDuration: "300ms" }}
    >
      <div
        role="button"
        tabIndex={0}
        onClick={() => onOpen(pr)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onOpen(pr);
          }
        }}
        className="group relative flex cursor-pointer items-start gap-4 py-3.5 pr-3 pl-4 transition-colors outline-none hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-inset sm:pl-5"
      >
        <span className="absolute inset-y-0 left-0 w-0.5" style={{ background: TIER_COLOR[pr.tier] }} aria-hidden />
        <div className="w-9 shrink-0 pt-0.5 text-right font-mono text-lg font-medium leading-6 tabular-nums">
          {pr.final_score}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-baseline gap-2">
            <a
              href={pr.url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="truncate text-[15px] font-medium text-zinc-900 hover:underline"
            >
              {pr.title}
            </a>
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
            <TierDot tier={pr.tier} className="size-1.5" />
            <span>{pr.tier}</span>
            <span className="text-zinc-300">·</span>
            <span className="font-mono">#{pr.number}</span>
            <span className="text-zinc-300">·</span>
            <span className="truncate">@{pr.author}</span>
          </div>
          <p className="mt-1.5 line-clamp-1 text-sm text-zinc-600">{pr.reason}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {ordered.map((name) => (
              <CheckBadge key={name} name={name} pr={pr} />
            ))}
            <span className="text-xs text-muted-foreground">
              {failed.length === 0 ? "All 7 checks passed" : `+${passed} passed`}
            </span>
          </div>
        </div>
        <ChevronRight className="mt-1 size-4 shrink-0 text-zinc-300 transition-colors group-hover:text-zinc-500" />
      </div>
    </li>
  );
}

function CheckBadge({ name, pr }: { name: CheckName; pr: PR }) {
  const flag = pr.rule_flags[name];
  const neutral = NEUTRAL_CHECKS.has(name);
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            onClick={(e) => e.stopPropagation()}
            className={cn(
              "inline-flex h-5 cursor-default items-center rounded-[5px] border px-1.5 text-[11px] font-medium",
              neutral
                ? "border-zinc-200 bg-zinc-50 text-zinc-600"
                : "border-[#E5484D]/25 bg-[#E5484D]/[0.06] text-(--fail-text)",
            )}
          />
        }
      >
        {checkLabel(name, flag)}
      </TooltipTrigger>
      <TooltipContent>{flag.note}</TooltipContent>
    </Tooltip>
  );
}
