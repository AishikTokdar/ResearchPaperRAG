/**
 * usePDFUpload Hook
 * 
 * Custom hook for managing PDF upload state and operations.
 * Handles single & multi-file upload (up to 3 PDFs, <= 10 pages each).
 */

import * as React from "react";
import { api, ApiError } from "@/lib/api";
import type { DocumentFileMeta } from "@/types";

interface PDFUploadState {
  isUploading: boolean;
  isLoaded: boolean;
  fileName: string | null;
  chunksCreated: number | null;
  files: DocumentFileMeta[];
  totalFiles: number;
  error: string | null;
}

interface UsePDFUploadReturn extends PDFUploadState {
  uploadPDF: (file: File) => Promise<void>;
  uploadPDFs: (files: File[]) => Promise<void>;
  reset: () => void;
}

const initialState: PDFUploadState = {
  isUploading: false,
  isLoaded: false,
  fileName: null,
  chunksCreated: null,
  files: [],
  totalFiles: 0,
  error: null,
};

export function usePDFUpload(): UsePDFUploadReturn {
  const [state, setState] = React.useState<PDFUploadState>(initialState);

  const uploadPDFs = React.useCallback(async (files: File[]) => {
    if (!files.length) return;
    if (files.length > 3) {
      setState((prev) => ({
        ...prev,
        error: "Maximum 3 PDF documents allowed per session.",
      }));
      return;
    }

    setState((prev) => ({
      ...prev,
      isUploading: true,
      error: null,
    }));

    try {
      const response = await api.uploadPDFs(files);

      setState({
        isUploading: false,
        isLoaded: true,
        fileName: response.file_name || files[0].name,
        chunksCreated: response.chunks_created,
        files: response.files || [],
        totalFiles: response.total_files || files.length,
        error: null,
      });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.detail
          : "Failed to upload PDF(s). Please try again.";

      setState((prev) => ({
        ...prev,
        isUploading: false,
        error: message,
      }));
    }
  }, []);

  const uploadPDF = React.useCallback(
    async (file: File) => {
      await uploadPDFs([file]);
    },
    [uploadPDFs],
  );

  const reset = React.useCallback(() => {
    setState(initialState);
  }, []);

  return {
    ...state,
    uploadPDF,
    uploadPDFs,
    reset,
  };
}
