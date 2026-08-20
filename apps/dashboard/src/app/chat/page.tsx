"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "@/hooks/useChat";
import { useAuth } from "@/hooks/useAuth";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";

const QUICK_QUERIES = [
  "Show today's production summary",
  "Top 5 products by waste this week",
  "Any temperature excursions today?",
  "Pending orders for this week",
];

export default function ChatPage() {
  const { messages, isLoading, streamingText, sendMessage, clearChat } = useChat();
  const { gate } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (gate === "login") router.push("/login");
  }, [gate, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  if (gate !== "ok") return null;

  return (
    <div className="flex h-full min-h-[calc(100vh-4rem)] flex-col">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white">Ask FloorMind</h1>
          <p className="text-sm text-zinc-500">
            Ask anything about your factory data, documents, or operations
          </p>
        </div>
        <button
          onClick={clearChat}
          className="rounded-lg border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:bg-zinc-900 hover:text-white"
        >
          Clear chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        {messages.length === 0 && (
          <div className="py-12 text-center text-zinc-400">
            <p className="text-lg">Ask a question to get started</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {QUICK_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-white"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} {...msg} />
        ))}

        {streamingText && <ChatMessage role="assistant" content={streamingText} />}

        {isLoading && !streamingText && (
          <div className="mb-4 flex justify-start">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900 px-4 py-3">
              <div className="flex gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400" />
                <span
                  className="h-2 w-2 animate-bounce rounded-full bg-zinc-400"
                  style={{ animationDelay: "0.1s" }}
                />
                <span
                  className="h-2 w-2 animate-bounce rounded-full bg-zinc-400"
                  style={{ animationDelay: "0.2s" }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}