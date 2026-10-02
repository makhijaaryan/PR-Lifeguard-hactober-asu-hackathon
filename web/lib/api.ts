// Client for the FastAPI server in /api. Types mirror contract.py.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Tier = "Review first" | "Needs info" | "Likely low-effort";

export type CheckName =
  | "links_issue"
  | "has_description"
  | "template_filled"
  | "touches_tests"
  | "size_ok"
  | "account_age_ok"
  | "returning_contributor";

export type Flag = { passed: boolean; note: string };

export type PR = {
  number: number;
  title: string;
  author: string;
  url: string;
  final_score: number;
  tier: Tier;
  reason: string;
  rule_flags: Record<CheckName, Flag>;
  guideline_issues: string[];
  description_matches_code: { value: boolean; note: string };
  draft_reply: string;
};

export type TriageResult = {
  repo: string;
  run_id: string;
  model_used: string;
  storage_backend: string;
  offline_demo?: boolean;
  prs: PR[];
};

export type Health = { model: string; storage_backend: string; llm_configured: boolean };

export type DemoRepo = { key: string; repo: string; count: number; model_used: string | null };

export type HistoryRow = {
  run_id: string;
  scored_at: string | null;
  repo: string;
  pr_number: number;
  title: string;
  author: string;
  url: string;
  final_score: number;
  tier: Tier;
  reason: string;
  failed_checks: string;
};

export type History = { rows: HistoryRow[]; source: string; storage_backend: string };

export const API_DOWN_MESSAGE =
  "Can't reach the PR Lifeguard API on port 8000. Start everything with ./dev.sh and try again.";

async function getJSON<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  } catch {
    throw new Error(API_DOWN_MESSAGE);
  }
  if (!res.ok) throw new Error(`The API returned ${res.status}. Try again in a moment.`);
  return res.json() as Promise<T>;
}

export const getHealth = () => getJSON<Health>("/api/health");
export const getDemoRepos = () => getJSON<{ repos: DemoRepo[] }>("/api/demo-repos");
export const getHistory = () => getJSON<History>("/api/history");

type TriageHandlers = {
  onProgress: (message: string, fraction: number) => void;
  signal?: AbortSignal;
};

/** POST /api/triage and read its Server-Sent Events. Resolves with the result, rejects with a friendly Error. */
export async function triage(
  body: { repo: string; limit: number; offline_demo: boolean },
  { onProgress, signal }: TriageHandlers,
): Promise<TriageResult> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/triage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new Error(API_DOWN_MESSAGE);
  }
  if (!res.ok || !res.body) throw new Error(`The API returned ${res.status}. Try again in a moment.`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split: number;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      let event = "message";
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      const payload = JSON.parse(data);
      if (event === "progress") onProgress(payload.message, payload.fraction);
      else if (event === "result") return payload as TriageResult;
      else if (event === "error") throw new Error(payload.message);
    }
  }
  throw new Error("The connection closed before triage finished. Try again.");
}
