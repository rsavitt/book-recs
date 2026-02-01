"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { SimilarUser } from "@/types";

export default function SimilarReadersPage() {
  const router = useRouter();
  const [similarUsers, setSimilarUsers] = useState<SimilarUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    loadSimilarUsers();
  }, [router]);

  const loadSimilarUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      const users = await api.getSimilarUsers(20);
      setSimilarUsers(users);
    } catch (err) {
      if (err instanceof Error && err.message.includes("401")) {
        router.push("/login");
        return;
      }
      setError("Failed to load similar readers");
    } finally {
      setLoading(false);
    }
  };

  const formatSimilarity = (score: number) => {
    return `${Math.round(score * 100)}%`;
  };

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
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Readers Like You</h1>
          <p className="text-gray-600 mt-1">
            People who share your taste in books. Your recommendations are powered by their ratings.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
          </div>
        ) : similarUsers.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl shadow">
            <div className="text-5xl mb-4">🔍</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              No similar readers found yet
            </h2>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              We need more data to find readers with similar taste. Try importing your Goodreads
              library or rating more books.
            </p>
            <Link
              href="/onboarding"
              className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              Import Your Library
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {similarUsers.map((user, index) => (
              <div
                key={user.username}
                className="bg-white rounded-xl shadow p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                      <span className="text-lg font-semibold text-purple-600">
                        #{index + 1}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {user.display_name || user.username}
                      </h3>
                      <p className="text-sm text-gray-500">@{user.username}</p>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-2xl font-bold text-purple-600">
                      {formatSimilarity(user.similarity_score)}
                    </div>
                    <div className="text-xs text-gray-500">match</div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="font-medium">{user.overlap_count}</span>
                    <span>books in common</span>
                  </div>

                  {user.shared_favorites.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs text-gray-500 mb-2">Books you both loved:</p>
                      <div className="flex flex-wrap gap-2">
                        {user.shared_favorites.slice(0, 5).map((book) => (
                          <span
                            key={book}
                            className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
                          >
                            {book}
                          </span>
                        ))}
                        {user.shared_favorites.length > 5 && (
                          <span className="px-2 py-1 text-gray-500 text-xs">
                            +{user.shared_favorites.length - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* How it works */}
        <div className="mt-12 bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold text-gray-900 mb-4">How Similarity Works</h2>
          <div className="space-y-3 text-sm text-gray-600">
            <p>
              <strong>Match percentage</strong> is calculated using Pearson correlation on the
              books you&apos;ve both rated. The more books you have in common, the more reliable
              the match.
            </p>
            <p>
              <strong>Books in common</strong> shows how many books you&apos;ve both read and
              rated. More overlap means better recommendations.
            </p>
            <p>
              <strong>Books you both loved</strong> are titles you both rated 4 or 5 stars.
              These shared favorites help explain why you matched.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
