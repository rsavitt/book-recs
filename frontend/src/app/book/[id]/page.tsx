"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { api } from "@/lib/api";
import type { Book } from "@/types";

export default function BookDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<string | null>(null);

  const bookId = params.id as string;

  useEffect(() => {
    if (bookId) {
      loadBook();
    }
  }, [bookId]);

  const loadBook = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.getBook(parseInt(bookId));
      setBook(data);
    } catch (err) {
      setError("Failed to load book details");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (feedback: "interested" | "not_interested" | "already_read") => {
    try {
      await api.submitFeedback(parseInt(bookId), feedback);
      setFeedbackSent(feedback);
    } catch {
      // Silent fail
    }
  };

  const renderSpiceLevel = (level: number | null) => {
    if (level === null) return "Unknown";
    if (level === 0) return "None (Closed door)";
    return "🌶️".repeat(level) + ` (Level ${level}/5)`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">{error || "Book not found"}</p>
          <button
            onClick={() => router.back()}
            className="text-purple-600 hover:text-purple-500"
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <span className="font-semibold text-xl text-gray-900">Romantasy Recs</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/recommendations" className="text-gray-600 hover:text-gray-900">
              Recommendations
            </Link>
            <Link href="/profile" className="text-gray-600 hover:text-gray-900">
              Profile
            </Link>
          </div>
        </nav>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back button */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <span>&larr;</span>
          <span>Back</span>
        </button>

        <div className="bg-white rounded-xl shadow overflow-hidden">
          <div className="md:flex">
            {/* Cover */}
            <div className="md:w-1/3 bg-gray-100">
              <div className="aspect-[2/3] relative">
                {book.cover_url ? (
                  <Image
                    src={book.cover_url}
                    alt={book.title}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, 33vw"
                    priority
                  />
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                    <span className="text-6xl">📚</span>
                  </div>
                )}
              </div>
            </div>

            {/* Details */}
            <div className="md:w-2/3 p-6 md:p-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900">
                {book.title}
              </h1>

              <p className="text-lg text-gray-600 mt-2">by {book.author}</p>

              {book.series_name && (
                <p className="text-gray-500 mt-1">
                  {book.series_name}
                  {book.series_position && ` #${book.series_position}`}
                </p>
              )}

              {/* Quick info */}
              <div className="flex flex-wrap gap-4 mt-6">
                {book.publication_year && (
                  <div className="text-sm">
                    <span className="text-gray-500">Published:</span>{" "}
                    <span className="text-gray-900">{book.publication_year}</span>
                  </div>
                )}
                {book.page_count && (
                  <div className="text-sm">
                    <span className="text-gray-500">Pages:</span>{" "}
                    <span className="text-gray-900">{book.page_count}</span>
                  </div>
                )}
                {book.is_ya !== null && (
                  <div className="text-sm">
                    <span className="text-gray-500">Category:</span>{" "}
                    <span className="text-gray-900">{book.is_ya ? "YA" : "Adult"}</span>
                  </div>
                )}
              </div>

              {/* Spice level */}
              {book.is_romantasy && (
                <div className="mt-4 p-3 bg-orange-50 rounded-lg">
                  <span className="text-sm font-medium text-orange-800">
                    Spice Level: {renderSpiceLevel(book.spice_level)}
                  </span>
                </div>
              )}

              {/* Tags */}
              {book.tags && book.tags.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {book.tags.map((tag) => (
                      <span
                        key={tag.id}
                        className="px-3 py-1 bg-purple-100 text-purple-700 text-sm rounded-full"
                      >
                        {tag.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {book.description && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                  <p className="text-gray-600 whitespace-pre-line">{book.description}</p>
                </div>
              )}

              {/* Feedback buttons */}
              {api.getToken() && (
                <div className="mt-8 pt-6 border-t border-gray-200">
                  {feedbackSent ? (
                    <div className="flex items-center gap-2 text-green-600">
                      <span>✓</span>
                      <span>
                        {feedbackSent === "interested" && "Added to your Want to Read list"}
                        {feedbackSent === "not_interested" && "Marked as not interested"}
                        {feedbackSent === "already_read" && "Marked as already read"}
                      </span>
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() => handleFeedback("interested")}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        Want to Read
                      </button>
                      <button
                        onClick={() => handleFeedback("already_read")}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                      >
                        Already Read
                      </button>
                      <button
                        onClick={() => handleFeedback("not_interested")}
                        className="px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        Not Interested
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* External links */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Find this book</h3>
                <div className="flex flex-wrap gap-3">
                  {book.isbn_13 && (
                    <a
                      href={`https://www.goodreads.com/search?q=${book.isbn_13}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-purple-600 hover:text-purple-500"
                    >
                      Goodreads
                    </a>
                  )}
                  {book.open_library_id && (
                    <a
                      href={`https://openlibrary.org/works/${book.open_library_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-purple-600 hover:text-purple-500"
                    >
                      Open Library
                    </a>
                  )}
                  <a
                    href={`https://www.amazon.com/s?k=${encodeURIComponent(
                      `${book.title} ${book.author}`
                    )}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-purple-600 hover:text-purple-500"
                  >
                    Amazon
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
