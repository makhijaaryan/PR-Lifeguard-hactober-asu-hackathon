import { ArrowRight, Check, Minus } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/footer";
import { LandingPreview } from "@/components/landing/preview";
import { LogoMark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { TierDot } from "@/components/triage/results-summary";
import { buttonVariants } from "@/components/ui/button";
import type { PR, Tier } from "@/lib/api";
import sample from "@/lib/landing-sample.json";
import { TIER_COLOR, TIERS } from "@/lib/tiers";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "PR Lifeguard: triage pull requests by effort",
  description:
    "Rank a repo's open pull requests by effort, not AI suspicion. Seven transparent checks, an open-weight LLM review and a kind draft reply for every PR.",
};

const preview = sample.preview as unknown as PR[];
const replyPR = sample.reply_example as unknown as PR;
const compare = sample.compare as { repo: string; total: number; avg: number; tiers: Record<Tier, number> }[];

// Weights mirror WEIGHTS in checks.py.
const CHECKS = [
  { name: "Linked issue", weight: 20, body: "Mentions “fixes #123”, “closes #45” or links an issue URL." },
  { name: "Has description", weight: 20, body: "At least a few real sentences once template comments are stripped." },
  { name: "Template filled", weight: 10, body: "Adds real text beyond the repo’s PR template. Passes if there is no template." },
  { name: "Tests touched", weight: 15, body: "Changes a test file. Docs-only changes aren’t expected to." },
  { name: "Focused size", weight: 15, body: "Not a 2-line typo tweak, not a 1,000-line dump." },
  { name: "Account age", weight: 5, body: "Account older than 30 days when the PR was opened.", neutral: true },
  { name: "Returning contributor", weight: 15, body: "Has merged work in this repo before.", neutral: true },
];

const PRINCIPLES = [
  { title: "Effort, not AI detection", body: "AI use can’t be detected reliably and isn’t the problem. A careful AI-assisted PR scores high; a careless one doesn’t." },
  { title: "Every score is explained", body: "Each number comes with the checks behind it, a one-line reason and the model’s notes. No black box." },
  { title: "Kind by default", body: "Draft replies thank the author and ask for the specific missing thing. They never accuse and never mention AI." },
  { title: "A human decides", body: "PR Lifeguard ranks and drafts. It never closes, labels or comments on its own." },
];

const RELIABILITY = [
  ["Two models", "On a rate limit, gpt-oss-120b hands off to Qwen with its own budget."],
  ["Rule-only fallback", "If both models are down, PRs are still scored from the seven checks, and the reason says so."],
  ["Storage fallback", "Results go to Snowflake when connected, local SQLite otherwise."],
  ["Offline demo", "Cached runs replay with no internet and no API keys."],
  ["Live progress", "Triage streams each step over Server-Sent Events, 4 PRs scored in parallel."],
];

const STACK = [
  { title: "Web app", items: ["Next.js App Router + TypeScript", "Tailwind + shadcn/ui", "Geist Sans & Mono, Recharts"] },
  { title: "API", items: ["FastAPI", "Server-Sent Events progress", "Offline demo cache"] },
  { title: "Engine", items: ["GitHub REST: PRs, diffs, guides", "7 rule checks + LLM review", "openai/gpt-oss-120b via Groq"] },
  { title: "Storage", items: ["PR_SCORES table", "Snowflake (optional)", "SQLite fallback"] },
];

export default function Landing() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <LogoMark className="size-6" />
            <span className="font-semibold tracking-tight">PR Lifeguard</span>
          </Link>
          <nav className="hidden items-center gap-5 text-sm text-muted-foreground md:flex">
            <a href="#problem" className="hover:text-foreground">Problem</a>
            <a href="#how" className="hover:text-foreground">How it works</a>
            <a href="#scoring" className="hover:text-foreground">Scoring</a>
            <a href="#architecture" className="hover:text-foreground">Architecture</a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <Link href="/app" className={cn(buttonVariants({ size: "lg" }), "px-3.5")}>
              Open the app <ArrowRight />
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-6xl px-4 pt-16 pb-12 sm:px-6 sm:pt-24">
          <div className="animate-in fade-in slide-in-from-bottom-1 max-w-3xl duration-500">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-zinc-600">
              <span className="size-1.5 rounded-full bg-emerald-600" />
              Hacktoberfest Hack Day · open-source AI
            </span>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-6xl sm:leading-[1.05]">
              Triage pull requests by effort, not by AI suspicion.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-pretty text-zinc-600">
              PR Lifeguard ranks a repo’s open pull requests by how much care went into them, explains every score,
              and drafts a kind reply for each one. Maintainers review the best work first. Everyone else gets a clear
              path to improve.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/app" className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-sm")}>
                Try it on a real repo <ArrowRight />
              </Link>
              <a href="#how" className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-11 bg-card px-5 text-sm")}>
                How it works
              </a>
            </div>
            <p className="mt-6 font-mono text-xs text-muted-foreground">
              7 transparent checks · open-weight LLM · 0–100 effort score · draft reply for every PR
            </p>
          </div>

          <div className="animate-in fade-in slide-in-from-bottom-2 mt-14 duration-700">
            <div className="overflow-hidden rounded-xl border border-border bg-zinc-100/60 p-2 shadow-sm">
              <div className="flex items-center justify-between px-2 pt-1 pb-2.5">
                <div className="flex gap-1.5">
                  <span className="size-2.5 rounded-full bg-zinc-300" />
                  <span className="size-2.5 rounded-full bg-zinc-300" />
                  <span className="size-2.5 rounded-full bg-zinc-300" />
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">real output from our demo runs</span>
                <span className="w-12" />
              </div>
              <LandingPreview prs={preview} />
            </div>
          </div>
        </section>

        {/* Problem */}
        <Section id="problem" kicker="The problem" title="Maintainers are drowning in low-effort pull requests.">
          <div className="grid gap-10 lg:grid-cols-2">
            <div className="space-y-4 text-[15px] leading-relaxed text-zinc-600">
              <p>
                Cheap AI tools made it trivial to open a pull request. Hacktoberfest 2026 stopped counting PRs because
                so many were one-line edits with no description, no issue and no tests.
              </p>
              <p>
                Today a maintainer has to open every one just to find that out. Banning AI is the wrong fix: plenty of
                great PRs are AI-assisted, and detectors are unreliable. The real signal is <b className="font-medium text-zinc-900">effort</b>:
                did the author explain the change, link an issue, add a test and keep it focused?
              </p>
            </div>
            <div className="space-y-3">
              {compare.map((r) => (
                <div key={r.repo} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate font-mono text-sm">{r.repo}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      avg <span className="font-mono text-zinc-900">{r.avg}</span> · {r.total} open PRs
                    </span>
                  </div>
                  <div className="mt-3 flex h-1.5 gap-0.5 overflow-hidden rounded-full">
                    {TIERS.filter((t) => r.tiers[t]).map((t) => (
                      <div key={t} style={{ flexGrow: r.tiers[t], background: TIER_COLOR[t] }} />
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-600">
                    {TIERS.map((t) => (
                      <span key={t} className="inline-flex items-center gap-1.5">
                        <TierDot tier={t} className="size-1.5" /> {t}
                        <span className="font-mono text-zinc-900">{r.tiers[t]}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              <p className="text-xs text-muted-foreground">
                Same tool, two very different queues: a Hacktoberfest tutorial repo vs a mature project.
              </p>
            </div>
          </div>
        </Section>

        {/* How it works */}
        <Section id="how" kicker="How it works" title="Paste a repo. Get a ranked, explained queue.">
          <ol className="grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
            {[
              ["Fetch", "Open PRs with their diffs, plus the repo’s CONTRIBUTING.md and PR template, straight from the GitHub API."],
              ["Score", "Seven rule checks and an open-weight LLM review each PR in parallel. Rules and model each count for half."],
              ["Reply", "Review the strongest PRs first. Copy a polite, specific draft reply for the rest."],
            ].map(([title, body], i) => (
              <li key={title} className="bg-card p-6">
                <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
                <h3 className="mt-3 font-medium">{title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </li>
            ))}
          </ol>
        </Section>

        {/* Scoring */}
        <Section id="scoring" kicker="Scoring" title="Transparent checks plus a model that reads the diff.">
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ul className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2">
                {CHECKS.map((c) => (
                  <li key={c.name} className="bg-card p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-sm font-medium">
                        {c.neutral ? <Minus className="size-3.5 text-zinc-400" /> : <Check className="size-3.5 text-emerald-600" />}
                        {c.name}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">{c.weight} pts</span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{c.body}</p>
                    {c.neutral && <p className="mt-1.5 text-xs text-zinc-500">Shown as grey context, never as a fault.</p>}
                  </li>
                ))}
                <li className="bg-card p-4">
                  <div className="text-sm font-medium">LLM review</div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Reads the description, a diff excerpt and CONTRIBUTING.md. Returns an effort score, a reason,
                    guideline issues, a description-vs-code check and a draft reply.
                  </p>
                </li>
              </ul>
            </div>
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-card p-5">
                <div className="text-sm font-medium">Final score</div>
                <pre className="mt-3 rounded-md bg-zinc-50 px-3 py-2.5 font-mono text-[13px] leading-relaxed text-zinc-800">
                  {"final = 0.5 × rules\n      + 0.5 × llm_effort"}
                </pre>
                <ul className="mt-4 space-y-2 text-sm">
                  {[
                    ["Review first", "70–100"],
                    ["Needs info", "40–69"],
                    ["Likely low-effort", "0–39"],
                  ].map(([t, range]) => (
                    <li key={t} className="flex items-center gap-2">
                      <span className="h-4 w-0.5 rounded-full" style={{ background: TIER_COLOR[t as Tier] }} />
                      <span className="text-zinc-700">{t}</span>
                      <span className="ml-auto font-mono text-xs text-muted-foreground">{range}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg border border-border bg-card p-5 text-sm text-muted-foreground">
                The model is told to judge effort and fit with the project’s rules, never whether AI was used, and never
                to claim anything it can’t see in the diff.
              </div>
            </div>
          </div>
        </Section>

        {/* Reply */}
        <Section kicker="Draft replies" title="Every PR gets a reply worth sending.">
          <div className="grid gap-8 lg:grid-cols-5">
            <div className="rounded-lg border border-border border-l-2 bg-card lg:col-span-3" style={{ borderLeftColor: TIER_COLOR[replyPR.tier] }}>
              <div className="flex items-center gap-2 border-b border-border px-5 py-3 text-xs text-muted-foreground">
                <TierDot tier={replyPR.tier} className="size-1.5" />
                <span>{replyPR.tier}</span>
                <span className="text-zinc-300">·</span>
                <span className="font-mono">#{replyPR.number}</span>
                <span className="text-zinc-300">·</span>
                <span className="truncate">{replyPR.title}</span>
                <span className="ml-auto font-mono text-zinc-900">{replyPR.final_score}</span>
              </div>
              <p className="p-5 text-[15px] leading-relaxed text-zinc-800">{replyPR.draft_reply}</p>
            </div>
            <ul className="space-y-4 lg:col-span-2">
              {[
                ["Thanks first", "Opens by thanking the contributor, especially first-timers."],
                ["Asks for one specific thing", "A linked issue, a description, a test or a smaller scope, based on what is missing."],
                ["Never accuses", "No “this looks AI-generated”. Effort is something anyone can add."],
              ].map(([t, b]) => (
                <li key={t}>
                  <div className="text-sm font-medium">{t}</div>
                  <p className="text-sm text-muted-foreground">{b}</p>
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* Principles */}
        <Section kicker="Principles" title="Built to be fair to contributors.">
          <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
            {PRINCIPLES.map((p) => (
              <div key={p.title} className="bg-card p-5">
                <h3 className="text-sm font-medium">{p.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Architecture */}
        <Section id="architecture" kicker="What we built" title="A full stack in one hack day.">
          <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
            {STACK.map((s, i) => (
              <div key={s.title} className="contents">
                <div className="flex-1 rounded-lg border border-border bg-card p-4">
                  <div className="text-sm font-medium">{s.title}</div>
                  <ul className="mt-2 space-y-1">
                    {s.items.map((it) => (
                      <li key={it} className="text-sm text-muted-foreground">{it}</li>
                    ))}
                  </ul>
                </div>
                {i < STACK.length - 1 && (
                  <ArrowRight className="mx-auto size-4 shrink-0 rotate-90 text-zinc-400 lg:rotate-0" aria-hidden />
                )}
              </div>
            ))}
          </div>
          <div className="mt-10 grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-5">
            {RELIABILITY.map(([t, b]) => (
              <div key={t} className="border-l border-border pl-4">
                <div className="text-sm font-medium">{t}</div>
                <p className="mt-1 text-sm text-muted-foreground">{b}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm text-muted-foreground">
            Plus an Insights dashboard (tier donut, score histogram, most-missed checks, sortable history), the original
            Streamlit UI as a backup, and Python tests for every layer.
          </p>
        </Section>

        {/* CTA */}
        <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
          <div className="flex flex-col items-start justify-between gap-6 rounded-xl border border-border bg-card p-8 sm:flex-row sm:items-center sm:p-10">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Give maintainers their time back.</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Try it on first-contributions, freeCodeCamp or home-assistant. Works offline with cached runs.
              </p>
            </div>
            <Link href="/app" className={cn(buttonVariants({ size: "lg" }), "h-11 shrink-0 px-5 text-sm")}>
              Open PR Lifeguard <ArrowRight />
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}

function Section({
  id,
  kicker,
  title,
  children,
}: {
  id?: string;
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-border">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <p className="font-mono text-xs text-muted-foreground">{kicker}</p>
        <h2 className="mt-2 max-w-2xl text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{title}</h2>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}
