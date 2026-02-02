"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Header } from "@/components/Header";
import { RecommendationCard } from "@/components/RecommendationCard";
import { BookCard } from "@/components/BookCard";
import type { Recommendation, BookTag, BookSearchResult } from "@/types";

type SpiceFilter = "any" | 0 | 1 | 2 | 3 | 4 | 5;
type AgeFilter = "any" | "ya" | "adult";
type ViewMode = "popular" | "quick" | "personalized";

export default function RecommendationsPage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("popular");
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick preferences
  const [popularBooks, setPopularBooks] = useState<BookSearchResult[]>([]);
  const [selectedBookIds, setSelectedBookIds] = useState<number[]>([]);
  const [showBookPicker, setShowBookPicker] = useState(false);

  // Filters
  const [spiceFilter, setSpiceFilter] = useState<SpiceFilter>("any");
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("any");
  const [selectedTropes, setSelectedTropes] = useState<string[]>([]);
  const [excludedTropes, setExcludedTropes] = useState<string[]>([]);
  const [availableTropes, setAvailableTropes] = useState<BookTag[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Dismissed books
  const [dismissedIds, setDismissedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    const token = api.getToken();
    setIsLoggedIn(!!token);

    if (token) {
      setViewMode("personalized");
    } else {
      setViewMode("popular");
      loadPopularBooks();
    }

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

  const loadPopularBooks = async () => {
    setLoading(true);
    try {
      const popular = await api.getPopularBooks(30);
      setRecommendations(popular);
      // Also store as book search results for the picker
      setPopularBooks(popular.map(p => ({
        id: p.book_id,
        title: p.title,
        author: p.author,
        cover_url: p.cover_url,
        spice_level: p.spice_level,
        is_ya: p.is_ya,
      })));
    } catch {
      setError("Failed to load popular books");
    } finally {
      setLoading(false);
    }
  };

  const loadPersonalizedRecommendations = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params: Parameters<typeof api.getRecommendations>[0] = {
        limit: 50,
      };

      if (spiceFilter !== "any") {
        params.spiceMin = spiceFilter;
        params.spiceMax = spiceFilter;
      }

      if (ageFilter === "ya") {
        params.isYa = true;
      } else if (ageFilter === "adult") {
        params.isYa = false;
      }

      if (selectedTropes.length > 0) {
        params.tropes = selectedTropes;
      }

      if (excludedTropes.length > 0) {
        params.excludeTropes = excludedTropes;
      }

      const recs = await api.getRecommendations(params);
      setRecommendations(recs);
    } catch (err) {
      if (err instanceof Error && err.message.includes("401")) {
        setIsLoggedIn(false);
        setViewMode("popular");
        loadPopularBooks();
        return;
      }
      setError("Failed to load recommendations. Try importing more books for better results.");
    } finally {
      setLoading(false);
    }
  }, [spiceFilter, ageFilter, selectedTropes, excludedTropes]);

  const loadQuickRecommendations = async () => {
    if (selectedBookIds.length === 0) {
      setError("Please select at least one book you like");
      return;
    }

    setLoading(true);
    setError(null);
    setShowBookPicker(false);

    try {
      const recs = await api.getQuickRecommendations(selectedBookIds, 30);
      setRecommendations(recs);
      setViewMode("quick");
    } catch {
      setError("Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (viewMode === "personalized" && isLoggedIn) {
      loadPersonalizedRecommendations();
    }
  }, [viewMode, isLoggedIn, loadPersonalizedRecommendations]);

  const handleFeedback = async (
    bookId: number,
    feedback: "interested" | "not_interested" | "already_read"
  ) => {
    if (!isLoggedIn) return;

    try {
      await api.submitFeedback(bookId, feedback);
      if (feedback === "not_interested" || feedback === "already_read") {
        setDismissedIds((prev) => new Set([...prev, bookId]));
      }
    } catch {
      // Silent fail
    }
  };

  const toggleBookSelection = (bookId: number) => {
    setSelectedBookIds(prev =>
      prev.includes(bookId)
        ? prev.filter(id => id !== bookId)
        : [...prev, bookId]
    );
  };

  const toggleTrope = (slug: string, list: "include" | "exclude") => {
    if (list === "include") {
      if (selectedTropes.includes(slug)) {
        setSelectedTropes(selectedTropes.filter((t) => t !== slug));
      } else {
        setSelectedTropes([...selectedTropes, slug]);
        setExcludedTropes(excludedTropes.filter((t) => t !== slug));
      }
    } else {
      if (excludedTropes.includes(slug)) {
        setExcludedTropes(excludedTropes.filter((t) => t !== slug));
      } else {
        setExcludedTropes([...excludedTropes, slug]);
        setSelectedTropes(selectedTropes.filter((t) => t !== slug));
      }
    }
  };

  const clearFilters = () => {
    setSpiceFilter("any");
    setAgeFilter("any");
    setSelectedTropes([]);
    setExcludedTropes([]);
  };

  const filteredRecs = recommendations.filter(
    (rec) => !dismissedIds.has(rec.book_id)
  );

  const hasActiveFilters =
    spiceFilter !== "any" ||
    ageFilter !== "any" ||
    selectedTropes.length > 0 ||
    excludedTropes.length > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {viewMode === "personalized"
                ? "Your Recommendations"
                : viewMode === "quick"
                ? "Quick Recommendations"
                : "Popular Romantasy Books"}
            </h1>
            <p className="text-gray-600 mt-1">
              {viewMode === "personalized"
                ? "Books loved by readers with similar taste"
                : viewMode === "quick"
                ? "Based on books you selected"
                : "Start discovering great reads"}
            </p>
          </div>

          <div className="flex gap-2">
            {viewMode === "personalized" && (
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <span>Filters</span>
                {hasActiveFilters && (
                  <span className="w-2 h-2 bg-purple-600 rounded-full" />
                )}
              </button>
            )}
          </div>
        </div>

        {/* Anonymous user actions */}
        {!isLoggedIn && (
          <div className="bg-white rounded-xl shadow p-6 mb-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
              <div>
                <h2 className="font-semibold text-gray-900">Get Better Recommendations</h2>
                <p className="text-gray-600 text-sm mt-1">
                  Select books you love for quick recs, or sign up for personalized recommendations
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowBookPicker(true)}
                  className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 font-medium"
                >
                  Pick Favorites
                </button>
                <Link
                  href="/register"
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
                >
                  Sign Up Free
                </Link>
              </div>
            </div>

            {/* Book picker */}
            {showBookPicker && (
              <div className="mt-6 border-t pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-900">
                    Select books you love ({selectedBookIds.length} selected)
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowBookPicker(false)}
                      className="px-3 py-1.5 text-gray-600 hover:text-gray-900"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={loadQuickRecommendations}
                      disabled={selectedBookIds.length === 0}
                      className="px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Get Recommendations
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
                  {popularBooks.map((book) => (
                    <button
                      key={book.id}
                      onClick={() => toggleBookSelection(book.id)}
                      className={`relative rounded-lg overflow-hidden transition-all ${
                        selectedBookIds.includes(book.id)
                          ? "ring-4 ring-purple-500 scale-105"
                          : "hover:scale-105"
                      }`}
                    >
                      {book.cover_url ? (
                        <img
                          src={book.cover_url}
                          alt={book.title}
                          className="w-full aspect-[2/3] object-cover"
                        />
                      ) : (
                        <div className="w-full aspect-[2/3] bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center p-2">
                          <span className="text-white text-xs text-center font-medium">
                            {book.title}
                          </span>
                        </div>
                      )}
                      {selectedBookIds.includes(book.id) && (
                        <div className="absolute inset-0 bg-purple-600/20 flex items-center justify-center">
                          <span className="text-2xl">✓</span>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* View mode tabs for anonymous users with quick recs */}
        {!isLoggedIn && viewMode === "quick" && (
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => {
                setViewMode("popular");
                loadPopularBooks();
              }}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              ← Back to Popular
            </button>
          </div>
        )}

        {/* Filters panel (logged in only) */}
        {showFilters && isLoggedIn && (
          <div className="bg-white rounded-xl shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Filter Recommendations</h2>
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
                  Tropes (click to include, double-click to exclude)
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableTropes.map((trope) => {
                    const isIncluded = selectedTropes.includes(trope.slug);
                    const isExcluded = excludedTropes.includes(trope.slug);

                    return (
                      <button
                        key={trope.slug}
                        onClick={() => toggleTrope(trope.slug, "include")}
                        onDoubleClick={() => toggleTrope(trope.slug, "exclude")}
                        className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                          isIncluded
                            ? "bg-purple-600 text-white"
                            : isExcluded
                            ? "bg-red-100 text-red-700 line-through"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        {trope.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
          </div>
        ) : filteredRecs.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📚</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              No recommendations yet
            </h2>
            <p className="text-gray-600 mb-6">
              {hasActiveFilters
                ? "Try adjusting your filters to see more books."
                : isLoggedIn
                ? "Import your Goodreads library or rate more books to get personalized recommendations."
                : "Select some books you like to get recommendations!"}
            </p>
            {!hasActiveFilters && isLoggedIn && (
              <Link
                href="/onboarding"
                className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Complete Onboarding
              </Link>
            )}
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">
              Showing {filteredRecs.length} {viewMode === "popular" ? "popular book" : "recommendation"}{filteredRecs.length !== 1 ? "s" : ""}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {filteredRecs.map((rec) => (
                <RecommendationCard
                  key={rec.book_id}
                  recommendation={rec}
                  onFeedback={isLoggedIn ? (feedback) => handleFeedback(rec.book_id, feedback) : undefined}
                  showFeedback={isLoggedIn}
                />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
