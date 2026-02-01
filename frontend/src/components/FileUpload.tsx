"use client";

import { useState, useCallback } from "react";

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  accept?: string;
  label?: string;
}

export function FileUpload({
  onUpload,
  accept = ".csv",
  label = "Upload Goodreads Export",
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setIsUploading(true);

      try {
        await onUpload(file);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setIsUploading(false);
      }
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  return (
    <div className="w-full">
      <label
        className={`
          flex flex-col items-center justify-center w-full h-48
          border-2 border-dashed rounded-lg cursor-pointer
          transition-colors
          ${
            isDragging
              ? "border-purple-500 bg-purple-50"
              : "border-gray-300 bg-gray-50 hover:bg-gray-100"
          }
          ${isUploading ? "opacity-50 cursor-not-allowed" : ""}
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          {isUploading ? (
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600" />
          ) : (
            <>
              <svg
                className="w-10 h-10 mb-3 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="mb-2 text-sm text-gray-500">
                <span className="font-semibold">{label}</span>
              </p>
              <p className="text-xs text-gray-500">
                Drag and drop or click to select
              </p>
            </>
          )}
        </div>
        <input
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleInputChange}
          disabled={isUploading}
        />
      </label>

      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}

      <div className="mt-4 text-sm text-gray-500">
        <p className="font-medium">How to get your Goodreads export:</p>
        <ol className="list-decimal list-inside mt-2 space-y-1">
          <li>Go to goodreads.com/review/import</li>
          <li>Click &quot;Export Library&quot;</li>
          <li>Download the CSV file</li>
          <li>Upload it here</li>
        </ol>
      </div>
    </div>
  );
}
