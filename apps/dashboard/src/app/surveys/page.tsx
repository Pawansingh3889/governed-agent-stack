"use client";

import { useQuery } from "@tanstack/react-query";
import { getSurveys } from "@/lib/api";
import { AlertTriangle, ClipboardList } from "lucide-react";

export default function SurveysPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["surveys"],
    queryFn: getSurveys,
    refetchInterval: 30000,
  });

  const surveys = Array.isArray(data) ? data : [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Surveys</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Governed survey authoring and conducting via elenchus. Authors build templates,
          respondents complete them through a conversational LLM-driven runner.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">elenchus is not reachable</span>
          </div>
          <p className="mt-2 text-sm text-amber-500/80">
            Start the elenchus backend, then set NEXT_PUBLIC_ELENCHUS_URL.
          </p>
        </div>
      ) : null}

      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Published Surveys</h2>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900/30" />
            ))}
          </div>
        ) : surveys.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center">
            <ClipboardList className="mx-auto h-8 w-8 text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">No published surveys yet.</p>
            <p className="mt-1 text-xs text-zinc-600">
              Author one in the elenchus app, then it appears here.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {surveys.slice(0, 20).map((s: { id: string; title: string; status?: string; run_count?: number }) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 px-5 py-4"
              >
                <div>
                  <h3 className="text-sm font-medium text-white">{s.title}</h3>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    {s.status ?? "published"}
                  </p>
                </div>
                <span className="rounded-full bg-zinc-800 px-2.5 py-1 text-xs text-zinc-400">
                  {s.run_count ?? 0} runs
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
