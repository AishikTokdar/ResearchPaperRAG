/**
 * useChat Hook
 *
 * Custom hook for managing chat state and operations.
 * Supports both standard JSON and SSE streaming responses.
 *
 * Usage:
 * const { chatHistory, isLoading, sendMessage, clearHistory } = useChat();
 *
 * Implementation note: ``sendMessageStreaming`` owns an ``AbortController`` in
 * ``abortRef`` so the UI can cancel in-flight SSE when the user navigates away
 * or hits Stop.
 */

import * as React from "react";
import { api, ApiError, streamQuestion } from "@/lib/api";
import { createChatEntry } from "@/lib/chat-history";
import type { ChatEntry } from "@/types";

interface ChatState {
  chatHistory: ChatEntry[];
  isLoading: boolean;
  error: string | null;
  streamingAnswer: string | null;
  statusMessage: string | null;
}

interface UseChatReturn extends ChatState {
  sendMessage: (message: string, model?: string, includeSources?: boolean, hybridMode?: boolean) => Promise<void>;
  sendMessageStreaming: (message: string, model?: string, includeSources?: boolean, hybridMode?: boolean) => void;
  clearHistory: () => void;
  cancelStream: () => void;
  setChatHistory: (entries: ChatEntry[]) => void;
}

const initialState: ChatState = {
  chatHistory: [],
  isLoading: false,
  error: null,
  streamingAnswer: null,
  statusMessage: null,
};

export function useChat(): UseChatReturn {
  const [state, setState] = React.useState<ChatState>(initialState);
  const abortRef = React.useRef<AbortController | null>(null);
  const streamGenerationRef = React.useRef(0);

  const sendMessage = React.useCallback(
    async (message: string, model?: string, includeSources?: boolean, hybridMode: boolean = true) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null, statusMessage: null }));

      try {
        const response = await api.askQuestion(message, model, includeSources ?? true, hybridMode);

        const newEntry = createChatEntry({
          question: message,
          answer: response.answer,
          sources: response.sources,
          modelUsed: response.model_used,
        });

        setState((prev) => ({
          ...prev,
          chatHistory: [...prev.chatHistory, newEntry],
          isLoading: false,
          error: null,
          statusMessage: null,
        }));
      } catch (error) {
        const errorMessage =
          error instanceof ApiError
            ? error.detail
            : "Failed to get response. Please check backend API keys and retry.";

        setState((prev) => ({ ...prev, isLoading: false, error: errorMessage, statusMessage: null }));
      }
    },
    [],
  );

  const sendMessageStreaming = React.useCallback(
    (message: string, model?: string, includeSources?: boolean, hybridMode: boolean = true) => {
      abortRef.current?.abort();
      const streamId = ++streamGenerationRef.current;

      setState((prev) => ({
        ...prev,
        isLoading: true,
        error: null,
        streamingAnswer: "",
        statusMessage: null,
      }));

      const questionRef = message;
      let accumulated = "";

      const controller = streamQuestion(
        { question: message, model, include_sources: includeSources ?? true, hybrid_mode: hybridMode, knowledge_mode: hybridMode ? "hybrid" : "strict" },
        {
          onStatus(_stage, msg) {
            if (streamId !== streamGenerationRef.current) return;
            setState((prev) => ({ ...prev, statusMessage: msg }));
          },
          onToken(text) {
            if (streamId !== streamGenerationRef.current) return;
            accumulated += text;
            setState((prev) => ({ ...prev, streamingAnswer: accumulated, statusMessage: null }));
          },
          onDone(meta) {
            if (streamId !== streamGenerationRef.current) return;
            const entry = createChatEntry({
              question: questionRef,
              answer: accumulated,
              sources: meta.sources,
              modelUsed: meta.model_used,
            });
            setState((prev) => ({
              ...prev,
              chatHistory: [...prev.chatHistory, entry],
              isLoading: false,
              streamingAnswer: null,
              statusMessage: null,
            }));
          },
          onError(msg) {
            if (streamId !== streamGenerationRef.current) return;
            setState((prev) => ({
              ...prev,
              isLoading: false,
              error: msg,
              streamingAnswer: null,
              statusMessage: null,
            }));
          },
        },
      );

      abortRef.current = controller;
    },
    [],
  );

  const cancelStream = React.useCallback(() => {
    // Abort fetch reader first, then normalize UI state.
    abortRef.current?.abort();
    streamGenerationRef.current += 1;
    setState((prev) => ({
      ...prev,
      isLoading: false,
      streamingAnswer: null,
    }));
  }, []);

  const clearHistory = React.useCallback(() => {
    abortRef.current?.abort();
    streamGenerationRef.current += 1;
    setState(initialState);
  }, []);

  const setChatHistory = React.useCallback((entries: ChatEntry[]) => {
    setState((prev) => ({ ...prev, chatHistory: entries }));
  }, []);

  return {
    ...state,
    sendMessage,
    sendMessageStreaming,
    clearHistory,
    cancelStream,
    setChatHistory,
  };
}
