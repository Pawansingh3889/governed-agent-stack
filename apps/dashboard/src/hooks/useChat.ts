"use client";

import { useCallback, useState } from "react";
import { chatStream, chatSync } from "@/lib/floor";
import type { ChatMessage, SSEEvent } from "@/lib/types";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");

  const sendMessage = useCallback(
    async (content: string, stream = true) => {
      const userMsg: ChatMessage = { role: "user", content };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setStreamingText("");

      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      if (!stream) {
        try {
          const result = await chatSync(content, history);
          const assistantMsg: ChatMessage = {
            role: "assistant",
            content: result.explanation,
            sql: result.sql,
            data: result.data,
            error: result.error,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        } catch (err) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `Error: ${err}`, error: true },
          ]);
        }
        setIsLoading(false);
        return;
      }

      let fullText = "";
      const resultBox: { current: SSEEvent | null } = { current: null };

      try {
        await chatStream(
          content,
          history,
          (token) => {
            fullText += token;
            setStreamingText(fullText);
          },
          (result) => {
            resultBox.current = result;
          }
        );

        const resultEvent = resultBox.current;
        if (resultEvent) {
          const assistantMsg: ChatMessage = {
            role: "assistant",
            content: resultEvent.explanation || fullText,
            sql: resultEvent.sql,
            data: resultEvent.data,
            error: resultEvent.error || false,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        } else {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: fullText },
          ]);
        }
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${err}`, error: true },
        ]);
      }

      setStreamingText("");
      setIsLoading(false);
    },
    [messages]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setStreamingText("");
  }, []);

  return { messages, isLoading, streamingText, sendMessage, clearChat };
}