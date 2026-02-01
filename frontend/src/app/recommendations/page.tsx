"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Header } from "@/components/Header";
import { RecommendationCard } from "@/components/RecommendationCard";
import type { Recommendation, BookTag } from "@/types";

type SpiceFilter = "any" | 0 | 1 | 2 | 3 | 4 | 5;
type AgeFilter = "any" | "ya" | "adult";

export default function RecommendationsPage() {
  const router = useRouter();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    if (!token) {
      router.push("/login");
      return;
    }
    loadTropes();
  }, [router]);

  const loadTropes = async () => {
    try {
      const tropes = await api.getTags("trope");
      setAvailableTropes(tropes);
    } catch {
      // Tropes are optional, continue without them
    }
  };

  const loadRecommendations = useCallback(async () => {
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
        router.push("/login");
        return;
      }
      setError("Failed to load recommendations. Try importing more books for better results.");
    } finally {
      setLoading(false);
    }
  }, [spiceFilter, ageFilter, selectedTropes, excludedTropes, router]);

  useEffect(() => {
    const token = api.getToken();
    if (token) {
      loadRecommendations();
    }
  }, [loadRecommendations]);

  const handleFeedback = async (
    bookId: number,
    feedback: "interested" | "not_interested" | "already_read"
  ) => {
    try {
      await api.submitFeedback(bookId, feedback);
      if (feedback === "not_interested" || feedback === "already_read") {
        setDismissedIds((prev) => new Set([...prev, bookId]));
      }
    } catch {
      // Silent fail for feedback
    }
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
            <h1 className="text-2xl font-bold text-gray-900">Your Recommendations</h1>
            <p className="text-gray-600 mt-1">
              Books loved by readers with similar taste
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
                : "Import your Goodreads library or rate more books to get personalized recommendations."}
            </p>
            {!hasActiveFilters && (
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
              Showing {filteredRecs.length} recommendation{filteredRecs.length !== 1 ? "s" : ""}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {filteredRecs.map((rec) => (
                <RecommendationCard
                  key={rec.book_id}
                  recommendation={rec}
                  onFeedback={(feedback) => {
                    handleFeedback(rec.book_id, feedback);
                  }}
                />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
