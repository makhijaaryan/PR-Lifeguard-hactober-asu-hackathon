"use client";

import Link from "next/link";
import { LogoMark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Switch } from "@/components/ui/switch";
import { TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Health } from "@/lib/api";

type Props = {
  health: Health | null;
  healthError: boolean;
  offline: boolean;
  onOfflineChange: (v: boolean) => void;
};

export function Navbar({ health, healthError, offline, onOfflineChange }: Props) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-2.5">
          <Link href="/" className="flex items-center gap-2.5 rounded-md focus-visible:ring-3 focus-visible:ring-primary/25 focus-visible:outline-none">
            <LogoMark className="size-6 shrink-0" />
            <span className="font-semibold tracking-tight">PR Lifeguard</span>
          </Link>
          <span className="hidden truncate text-sm text-muted-foreground lg:inline">
            Effort-based triage for open-source pull requests
          </span>
        </div>

        <TabsList variant="line" className="ml-2 h-14 gap-4 sm:ml-6">
          <TabsTrigger value="triage" className="px-0.5">Triage</TabsTrigger>
          <TabsTrigger value="insights" className="px-0.5">Insights</TabsTrigger>
        </TabsList>

        <div className="ml-auto flex items-center gap-4">
          <div className="hidden items-center gap-3 font-mono text-xs text-muted-foreground md:flex">
            {healthError ? (
              <span className="flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-zinc-400" /> API offline
              </span>
            ) : (
              <>
                <span title="Model">{health ? shortModel(health.model) : "…"}</span>
                <span className="text-zinc-300">/</span>
                <span title="Storage">{health?.storage_backend ?? "…"}</span>
              </>
            )}
          </div>
          <Tooltip>
            <TooltipTrigger
              render={
                <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-700 select-none" />
              }
            >
              <Switch
                checked={offline}
                onCheckedChange={onOfflineChange}
                aria-label="Offline demo"
                className="data-checked:bg-zinc-900 focus-visible:ring-primary/25"
              />
              <span className="hidden sm:inline">Offline demo</span>
              <span className="sm:hidden">Offline</span>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-64">
              Replays cached results for repos triaged before. Works with no internet or API keys.
            </TooltipContent>
          </Tooltip>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function shortModel(model: string) {
  return model.split("/").pop() ?? model;
}
