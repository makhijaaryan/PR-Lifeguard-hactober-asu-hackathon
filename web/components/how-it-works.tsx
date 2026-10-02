const STEPS = [
  {
    title: "Paste a repo",
    body: "Any public GitHub repository. We read its open PRs, diffs, CONTRIBUTING.md and PR template.",
  },
  {
    title: "Score effort",
    body: "Seven transparent checks plus an open-weight LLM review give each PR a 0–100 effort score. Not AI detection.",
  },
  {
    title: "Reply kindly",
    body: "Review the strongest PRs first and send everyone else a specific, polite draft reply.",
  },
];

export function HowItWorks() {
  return (
    <section className="animate-in fade-in duration-500">
      <h2 className="text-sm font-medium text-zinc-900">How it works</h2>
      <ol className="mt-3 grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step.title} className="bg-card p-5">
            <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
            <h3 className="mt-2 text-sm font-medium">{step.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
