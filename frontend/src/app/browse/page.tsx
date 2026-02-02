"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { BookCard } from "@/components/BookCard";
import type { BookSearchResult, BookTag } from "@/types";

type SpiceFilter = "any" | 0 | 1 | 2 | 3 | 4 | 5;
type AgeFilter = "any" | "ya" | "adult";

export default function BrowsePage() {
  const [books, setBooks] = useState<BookSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Filters
  const [spiceFilter, setSpiceFilter] = useState<SpiceFilter>("any");
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("any");
  const [selectedTropes, setSelectedTropes] = useState<string[]>([]);
  const [availableTropes, setAvailableTropes] = useState<BookTag[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Pagination
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 24;

  // Check auth status after hydration to avoid SSR mismatch
  useEffect(() => {
    setIsLoggedIn(!!api.getToken());
  }, []);

  useEffect(() => {
    loadTropes();
  }, []);

  const loadTropes = async () => {
    try {
      const tropes = await api.getTags("trope");
      setAvailableTropes(tropes);
    } catch {
      // Tropes are optional
    }
  };

  const loadBooks = useCallback(async (reset = false) => {
    setLoading(true);
    setError(null);

    const currentOffset = reset ? 0 : offset;

    try {
      const params: Parameters<typeof api.listRomantasyBooks>[0] = {
        limit: LIMIT,
        offset: currentOffset,
      };

      if (spiceFilter !== "any") {
        params.spiceLevel = spiceFilter;
      }

      if (ageFilter === "ya") {
        params.isYa = true;
      } else if (ageFilter === "adult") {
        params.isYa = false;
      }

      if (selectedTropes.length > 0) {
        params.tropes = selectedTropes;
      }

      const results = await api.listRomantasyBooks(params);

      if (reset) {
        setBooks(results);
        setOffset(LIMIT);
      } else {
        setBooks((prev) => [...prev, ...results]);
        setOffset((prev) => prev + LIMIT);
      }

      setHasMore(results.length === LIMIT);
    } catch {
      setError("Failed to load books");
    } finally {
      setLoading(false);
    }
  }, [spiceFilter, ageFilter, selectedTropes, offset]);

  // Load on filter change
  useEffect(() => {
    loadBooks(true);
  }, [spiceFilter, ageFilter, selectedTropes, loadBooks]);

  const toggleTrope = (slug: string) => {
    if (selectedTropes.includes(slug)) {
      setSelectedTropes(selectedTropes.filter((t) => t !== slug));
    } else {
      setSelectedTropes([...selectedTropes, slug]);
    }
  };

  const clearFilters = () => {
    setSpiceFilter("any");
    setAgeFilter("any");
    setSelectedTropes([]);
  };

  const hasActiveFilters =
    spiceFilter !== "any" || ageFilter !== "any" || selectedTropes.length > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <span className="font-semibold text-xl text-gray-900">Romantasy Recs</span>
          </Link>
          <div className="flex items-center gap-4">
            {isLoggedIn ? (
              <>
                <Link href="/recommendations" className="text-gray-600 hover:text-gray-900">
                  My Recs
                </Link>
                <Link href="/profile" className="text-gray-600 hover:text-gray-900">
                  Profile
                </Link>
              </>
            ) : (
              <>
                <Link href="/login" className="text-gray-600 hover:text-gray-900">
                  Log in
                </Link>
                <Link
                  href="/register"
                  className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Browse Romantasy</h1>
            <p className="text-gray-600 mt-1">
              Explore our collection of fantasy romance books
            </p>
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="w-2 h-2 bg-purple-600 rounded-full" />
            )}
          </button>
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="bg-white rounded-xl shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Filter Books</h2>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-purple-600 hover:text-purple-500"
                >
                  Clear all
                </button>
              )}
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Spice level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Spice Level
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setSpiceFilter("any")}
                    className={`px-3 py-1.5 rounded-full text-sm ${
                      spiceFilter === "any"
                        ? "bg-purple-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    Any
                  </button>
                  {[0, 1, 2, 3, 4, 5].map((level) => (
                    <button
                      key={level}
                      onClick={() => setSpiceFilter(level as SpiceFilter)}
                      className={`px-3 py-1.5 rounded-full text-sm ${
                        spiceFilter === level
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {level === 0 ? "None" : "🌶️".repeat(level)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Age category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Age Category
                </label>
                <div className="flex gap-2">
                  {[
                    { value: "any", label: "Any" },
                    { value: "ya", label: "YA" },
                    { value: "adult", label: "Adult" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setAgeFilter(opt.value as AgeFilter)}
                      className={`px-4 py-1.5 rounded-full text-sm ${
                        ageFilter === opt.value
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Tropes */}
            {availableTropes.length > 0 && (
              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tropes
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableTropes.map((trope) => (
                    <button
                      key={trope.slug}
                      onClick={() => toggleTrope(trope.slug)}
                      className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                        selectedTropes.includes(trope.slug)
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {trope.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Books grid */}
        {books.length === 0 && !loading ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📚</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No books found</h2>
            <p className="text-gray-600">
              {hasActiveFilters
                ? "Try adjusting your filters to see more books."
                : "Check back soon for new additions!"}
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {books.map((book) => (
                <Link key={book.id} href={`/book/${book.id}`}>
                  <BookCard book={book} />
                </Link>
              ))}
            </div>

            {/* Load more */}
            {hasMore && (
              <div className="mt-8 text-center">
                <button
                  onClick={() => loadBooks(false)}
                  disabled={loading}
                  className="px-6 py-3 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  {loading ? "Loading..." : "Load More"}
                </button>
              </div>
            )}
          </>
        )}

        {/* Loading state for initial load */}
        {loading && books.length === 0 && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
          </div>
        )}

        {/* Sign up CTA for non-logged-in users */}
        {!isLoggedIn && books.length > 0 && (
          <div className="mt-12 bg-purple-50 rounded-xl p-8 text-center">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Want Personalized Recommendations?
            </h2>
            <p className="text-gray-600 mb-6">
              Import your Goodreads library and we&apos;ll find books you&apos;ll love based on
              readers with similar taste.
            </p>
            <Link
              href="/register"
              className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              Get Started Free
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
