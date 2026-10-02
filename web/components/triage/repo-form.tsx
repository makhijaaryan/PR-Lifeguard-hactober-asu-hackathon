"use client";

import { CornerDownLeft, Minus, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export const SAMPLE_REPOS = [
  { label: "first-contributions", repo: "firstcontributions/first-contributions" },
  { label: "freeCodeCamp", repo: "freeCodeCamp/freeCodeCamp" },
  { label: "home-assistant", repo: "home-assistant/core" },
];
export const MIN_PRS = 5;
export const MAX_PRS = 25;

type Props = {
  repo: string;
  onRepoChange: (v: string) => void;
  limit: number;
  onLimitChange: (v: number) => void;
  onSubmit: (repo?: string) => void;
  busy: boolean;
  cachedKeys: Set<string>;
  offline: boolean;
};

export function RepoForm({ repo, onRepoChange, limit, onLimitChange, onSubmit, busy, cachedKeys, offline }: Props) {
  const clamp = (n: number) => Math.max(MIN_PRS, Math.min(MAX_PRS, n));
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="space-y-3"
    >
      <div className="flex flex-col gap-2 sm:flex-row">
        <label className="group flex h-11 min-w-0 flex-1 items-center gap-2.5 rounded-lg border border-border bg-card px-3 shadow-sm transition-colors focus-within:border-primary focus-within:ring-3 focus-within:ring-primary/15">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <input
            value={repo}
            onChange={(e) => onRepoChange(e.target.value)}
            placeholder="owner/repo or https://github.com/owner/repo"
            aria-label="GitHub repository"
            spellCheck={false}
            autoComplete="off"
            className="h-full min-w-0 flex-1 bg-transparent font-mono text-sm outline-none placeholder:font-sans placeholder:text-muted-foreground"
          />
          <Kbd className="hidden sm:inline-flex">
            <CornerDownLeft className="size-3" />
          </Kbd>
        </label>

        <div className="flex gap-2">
          <div className="flex h-11 items-center rounded-lg border border-border bg-card shadow-sm" aria-label="Max PRs">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="ml-1 text-muted-foreground"
              aria-label="Fewer PRs"
              disabled={limit <= MIN_PRS}
              onClick={() => onLimitChange(clamp(limit - 1))}
            >
              <Minus />
            </Button>
            <div className="w-16 text-center leading-none">
              <div className="font-mono text-sm tabular-nums">{limit}</div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">max PRs</div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="mr-1 text-muted-foreground"
              aria-label="More PRs"
              disabled={limit >= MAX_PRS}
              onClick={() => onLimitChange(clamp(limit + 1))}
            >
              <Plus />
            </Button>
          </div>
          <Button type="submit" disabled={busy || !repo.trim()} className="h-11 flex-1 px-5 text-sm sm:flex-none">
            {busy ? "Triaging…" : "Triage PRs"}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Try</span>
        {SAMPLE_REPOS.map((s) => {
          const cached = cachedKeys.has(s.repo.toLowerCase());
          return (
            <Tooltip key={s.repo}>
              <TooltipTrigger
                render={
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      onRepoChange(s.repo);
                      onSubmit(s.repo);
                    }}
                    className={cn(
                      "inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 font-mono text-xs text-zinc-700 transition-colors",
                      "hover:border-zinc-300 hover:bg-zinc-50 focus-visible:border-primary focus-visible:ring-3 focus-visible:ring-primary/15 focus-visible:outline-none disabled:opacity-50",
                    )}
                  />
                }
              >
                {cached && <span className="size-1.5 rounded-full bg-zinc-400" aria-hidden />}
                {s.label}
              </TooltipTrigger>
              <TooltipContent>
                {s.repo}
                {cached ? " · cached for offline demo" : offline ? " · not cached yet" : ""}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </form>
  );
}
