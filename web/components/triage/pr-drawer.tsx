"use client";

import { Check, Copy, ExternalLink, Minus, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { PR } from "@/lib/api";
import { CHECK_ORDER, checkLabel, NEUTRAL_CHECKS, TIER_COLOR } from "@/lib/tiers";
import { TierDot } from "./results-summary";

export function PRDrawer({ pr, onClose }: { pr: PR | null; onClose: () => void }) {
  return (
    <Sheet open={!!pr} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto border-l border-border p-0 shadow-sm data-[side=right]:w-full data-[side=right]:sm:max-w-[520px]">
        {pr && <DrawerBody pr={pr} />}
      </SheetContent>
    </Sheet>
  );
}

function DrawerBody({ pr }: { pr: PR }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(pr.draft_reply);
      setCopied(true);
      toast.success("Draft reply copied", { description: `Paste it on #${pr.number} when you're ready.` });
      setTimeout(() => setCopied(false), 1600);
    } catch {
      toast.error("Couldn't copy automatically", { description: "Select the reply text and copy it manually." });
    }
  };

  return (
    <>
      <SheetHeader className="gap-3 border-b border-border p-5 pr-12">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <TierDot tier={pr.tier} />
          <span style={{ color: TIER_COLOR[pr.tier] }} className="font-medium">
            {pr.tier}
          </span>
          <span className="text-zinc-300">·</span>
          <span className="font-mono">#{pr.number}</span>
          <span className="text-zinc-300">·</span>
          <span>@{pr.author}</span>
        </div>
        <SheetTitle className="text-lg leading-snug font-semibold">{pr.title}</SheetTitle>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="font-mono text-4xl font-medium tabular-nums">{pr.final_score}</div>
            <div className="text-xs text-muted-foreground">effort score / 100</div>
          </div>
          <a
            href={pr.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm text-zinc-700 hover:text-zinc-900 hover:underline"
          >
            Open on GitHub <ExternalLink className="size-3.5" />
          </a>
        </div>
        <SheetDescription className="text-sm leading-relaxed text-zinc-700">{pr.reason}</SheetDescription>
      </SheetHeader>

      <div className="space-y-7 p-5">
        <Section title="Draft reply">
          <div className="rounded-lg border border-border bg-zinc-50/70">
            <p className="p-4 text-sm leading-relaxed whitespace-pre-wrap text-zinc-800">{pr.draft_reply}</p>
            <div className="flex items-center justify-between border-t border-border px-3 py-2">
              <span className="text-xs text-muted-foreground">Review before posting</span>
              <Button size="sm" variant="outline" onClick={copy} className="bg-card">
                {copied ? <Check /> : <Copy />}
                {copied ? "Copied" : "Copy reply"}
              </Button>
            </div>
          </div>
        </Section>

        <Section title="Checks">
          <ul className="divide-y divide-border rounded-lg border border-border">
            {CHECK_ORDER.map((name) => {
              const flag = pr.rule_flags[name];
              if (!flag) return null;
              const neutral = NEUTRAL_CHECKS.has(name) && !flag.passed;
              return (
                <li key={name} className="flex items-start gap-3 px-3 py-2.5">
                  <span
                    className={
                      "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full " +
                      (flag.passed
                        ? "bg-emerald-600/10 text-emerald-700"
                        : neutral
                          ? "bg-zinc-100 text-zinc-500"
                          : "bg-[#E5484D]/10 text-[#C8323A]")
                    }
                  >
                    {flag.passed ? <Check className="size-3" /> : neutral ? <Minus className="size-3" /> : <X className="size-3" />}
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{checkLabel(name, flag)}</div>
                    <div className="text-sm text-muted-foreground">{flag.note}</div>
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">
            Grey items are context about the contributor, not a fault.
          </p>
        </Section>

        <Section title="Contributing guidelines">
          {pr.guideline_issues.length ? (
            <ul className="space-y-1.5">
              {pr.guideline_issues.map((issue) => (
                <li key={issue} className="flex gap-2 text-sm text-zinc-700">
                  <span className="mt-2 size-1 shrink-0 rounded-full bg-amber-500" />
                  {issue}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No guideline issues found.</p>
          )}
        </Section>

        <Section title="Description matches code">
          <div className="flex items-start gap-2 text-sm">
            <span
              className={
                "mt-0.5 shrink-0 rounded px-1.5 py-px font-mono text-[11px] font-medium " +
                (pr.description_matches_code.value ? "bg-emerald-600/10 text-emerald-700" : "bg-[#E5484D]/10 text-[#C8323A]")
              }
            >
              {pr.description_matches_code.value ? "YES" : "NO"}
            </span>
            <span className="text-zinc-700">{pr.description_matches_code.note || "No note from the model."}</span>
          </div>
        </Section>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2.5 text-sm font-medium text-zinc-900">{title}</h3>
      {children}
    </section>
  );
}
