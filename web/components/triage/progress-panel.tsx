import { Skeleton } from "@/components/ui/skeleton";

export function ProgressPanel({ message, fraction }: { message: string; fraction: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, fraction)) * 100);
  return (
    <section className="animate-in fade-in duration-300" aria-live="polite" aria-busy="true">
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-zinc-700">{message}</span>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">{pct}%</span>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-zinc-200/70">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      <div className="mt-6 overflow-hidden rounded-lg border border-border bg-card">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 border-b border-border px-4 py-4 last:border-b-0">
            <Skeleton className="h-6 w-8" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4" style={{ width: `${60 - i * 6}%` }} />
              <Skeleton className="h-3 w-1/3" />
            </div>
            <Skeleton className="hidden h-5 w-24 sm:block" />
          </div>
        ))}
      </div>
    </section>
  );
}
