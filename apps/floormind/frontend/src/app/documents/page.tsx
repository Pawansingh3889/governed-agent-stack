"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDocumentCount, searchDocuments, uploadDocument } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";

export default function DocumentsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<
    { text: string; score: number; source: string; category: string }[]
  >([]);
  const [docCount, setDocCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("fm_token");
    if (!token) { router.push("/"); return; }
    getDocumentCount().then((d) => setDocCount(d.count)).catch(console.error);
  }, [router]);

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
      setUploadMsg(`Ingested ${res.filename} — ${res.chunk_count} chunks`);
      setDocCount((c) => c + res.chunk_count);
    } catch (err) {
      setUploadMsg(`Error: ${err}`);
    }
    setUploading(false);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 pb-20 md:pb-6 max-w-4xl">
        <h1 className="text-2xl font-bold mb-6">🔍 Document Search</h1>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 mb-6">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search SOPs, HACCP plans, specifications..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            className="px-6 py-3 bg-brand-500 text-white rounded-xl hover:bg-brand-600"
          >
            Search
          </button>
        </form>

        {/* Results */}
        <div className="space-y-3 mb-8">
          {results.map((r, i) => (
            <div key={i} className="bg-white rounded-xl border p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium text-sm">📄 {r.source}</span>
                <span className="text-xs text-gray-400">
                  {Math.round(r.score * 100)}% match | {r.category}
                </span>
              </div>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{r.text}</p>
            </div>
          ))}
        </div>

        {/* Upload */}
        <section className="bg-white rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4">📁 Upload Documents</h2>
          <p className="text-sm text-gray-500 mb-4">
            Upload SOPs, HACCP plans, customer specs, audit reports (PDF)
          </p>
          <input
            type="file"
            accept=".pdf"
            onChange={handleUpload}
            disabled={uploading}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
          />
          {uploading && <p className="text-sm text-gray-500 mt-2">Uploading...</p>}
          {uploadMsg && <p className="text-sm text-green-600 mt-2">{uploadMsg}</p>}
          <p className="text-xs text-gray-400 mt-4">
            Total document chunks indexed: {docCount}
          </p>
        </section>
      </main>
    </div>
  );
}
