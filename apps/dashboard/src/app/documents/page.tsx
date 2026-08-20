"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDocumentCount, searchDocuments, uploadDocument } from "@/lib/floor";
import { useAuth } from "@/hooks/useAuth";

export default function DocumentsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<
    { text: string; score: number; source: string; category: string }[]
  >([]);
  const [docCount, setDocCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const { gate } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (gate === "login") {
      router.push("/login");
      return;
    }
    if (gate !== "ok") return;
    getDocumentCount().then((d) => setDocCount(d.count)).catch(console.error);
  }, [gate, router]);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    const res = await searchDocuments(query);
    setResults(res);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg("");
    try {
      const res = await uploadDocument(file);
      setUploadMsg(`Ingested ${res.filename} - ${res.chunk_count} chunks`);
      setDocCount((c) => c + res.chunk_count);
    } catch (err) {
      setUploadMsg(`Error: ${err}`);
    }
    setUploading(false);
  };

  if (gate !== "ok") return null;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Document Search</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Search SOPs, HACCP plans and specifications indexed by FloorMind
        </p>
      </header>

      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search SOPs, HACCP plans, specifications..."
          className="flex-1 rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-3 text-sm text-zinc-200 placeholder-zinc-500 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          type="submit"
          className="rounded-xl bg-brand-500 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-brand-600"
        >
          Search
        </button>
      </form>

      <div className="space-y-3">
        {results.map((r, i) => (
          <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-white">{r.source}</span>
              <span className="text-xs text-zinc-500">
                {Math.round(r.score * 100)}% match | {r.category}
              </span>
            </div>
            <p className="whitespace-pre-wrap text-sm text-zinc-300">{r.text}</p>
          </div>
        ))}
      </div>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Upload Documents</h2>
        <p className="mb-4 text-sm text-zinc-500">
          Upload SOPs, HACCP plans, customer specs, audit reports (PDF)
        </p>
        <input
          type="file"
          accept=".pdf"
          onChange={handleUpload}
          disabled={uploading}
          className="block w-full text-sm text-zinc-400 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-500 file:px-4 file:py-2 file:font-semibold file:text-white hover:file:bg-brand-600"
        />
        {uploading && <p className="mt-2 text-sm text-zinc-500">Uploading...</p>}
        {uploadMsg && <p className="mt-2 text-sm text-green-400">{uploadMsg}</p>}
        <p className="mt-4 text-xs text-zinc-500">
          Total document chunks indexed: {docCount}
        </p>
      </section>
    </div>
  );
}