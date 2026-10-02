"use client";

import { useRouter } from "next/navigation";
import { PRList } from "@/components/triage/pr-list";
import type { PR } from "@/lib/api";

/** Real rows from the demo cache, rendered with the app's own list component. Clicking opens the app. */
export function LandingPreview({ prs }: { prs: PR[] }) {
  const router = useRouter();
  return <PRList prs={prs} onOpen={() => router.push("/app")} />;
}
