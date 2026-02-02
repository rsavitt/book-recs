"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { api } from "@/lib/api";
import { FileUpload } from "@/components/FileUpload";

type Step = "import" | "preferences" | "rate-books" | "complete";

interface StarterBook {
  id: number;
  title: string;
  author: string;
  cover_url: string | null;
  series_name: string | null;
  spice_level: number | null;
  is_ya: boolean | null;
  tags: string[];
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("import");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preferences state
  const [spicePreference, setSpicePreference] = useState<number | null>(null);
  const [prefersYa, setPrefersYa] = useState<boolean | null>(null);

  // Book rating state
  const [starterBooks, setStarterBooks] = useState<StarterBook[]>([]);
  const [ratings, setRatings] = useState<Record<number, number>>({});

  useEffect(() => {
    // Check if user is authenticated
    const token = api.getToken();
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  const handleImport = async (file: File) => {
    setError(null);
    try {
      await api.importGoodreads(file);
      // Move to preferences after import starts
      setStep("preferences");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    }
  };

  const handleSkipImport = () => {
    setStep("preferences");
  };

  const handleSavePreferences = async () => {
    setLoading(true);
    setError(null);

    try {
      await api.updatePreferences({
        spice_preference: spicePreference,
        prefers_ya: prefersYa,
      });
      setStep("rate-books");
      loadStarterBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preferences");
    } finally {
      setLoading(false);
    }
  };

  const loadStarterBooks = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/onboarding/starter-books`,
        {
          headers: {
            Authorization: `Bearer ${api.getToken()}`,
          },
        }
      );
      const books = await response.json();
      setStarterBooks(books);
    } catch {
      setError("Failed to load books");
    } finally {
      setLoading(false);
    }
  };

  const handleRateBook = (bookId: number, rating: number) => {
    setRatings((prev) => ({ ...prev, [bookId]: rating }));
  };

  const handleSubmitRatings = async () => {
    const ratingsList = Object.entries(ratings).map(([bookId, rating]) => ({
      book_id: parseInt(bookId),
      rating,
    }));

    if (ratingsList.length < 5) {
      setError("Please rate at least 5 books to get personalized recommendations");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/onboarding/starter-ratings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${api.getToken()}`,
        },
        body: JSON.stringify({ ratings: ratingsList }),
      });
      setStep("complete");
    } catch {
      setError("Failed to save ratings");
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    switch (step) {
      case "import":
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900">Import Your Library</h2>
              <p className="mt-2 text-gray-600">
                Upload your Goodreads export to get personalized recommendations
              </p>
            </div>

            <FileUpload onUpload={handleImport} />

            <div className="text-center">
              <button
                onClick={handleSkipImport}
                className="text-purple-600 hover:text-purple-500 text-sm font-medium"
              >
                Skip for now - I&apos;ll rate books manually
              </button>
            </div>
          </div>
        );

      case "preferences":
        return (
          <div className="space-y-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900">Set Your Preferences</h2>
              <p className="mt-2 text-gray-600">
                Help us understand what you&apos;re looking for
              </p>
            </div>

            {/* Spice Level */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Preferred Spice Level
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {[0, 1, 2, 3, 4, 5].map((level) => (
                  <button
                    key={level}
                    onClick={() => setSpicePreference(level)}
                    className={`p-3 rounded-lg border-2 text-center transition-colors ${
                      spicePreference === level
                        ? "border-purple-500 bg-purple-50"
                        : "border-gray-200 hover:border-purple-300"
                    }`}
                  >
                    <div className="text-lg">{"🌶️".repeat(level) || "😇"}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {level === 0 && "None"}
                      {level === 1 && "Mild"}
                      {level === 2 && "Warm"}
                      {level === 3 && "Hot"}
                      {level === 4 && "Spicy"}
                      {level === 5 && "🔥🔥🔥"}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* YA Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Age Category Preference
              </label>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => setPrefersYa(true)}
                  className={`p-4 rounded-lg border-2 text-center transition-colors ${
                    prefersYa === true
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-200 hover:border-purple-300"
                  }`}
                >
                  <div className="font-medium">YA</div>
                  <div className="text-xs text-gray-500">Young Adult</div>
                </button>
                <button
                  onClick={() => setPrefersYa(false)}
                  className={`p-4 rounded-lg border-2 text-center transition-colors ${
                    prefersYa === false
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-200 hover:border-purple-300"
                  }`}
                >
                  <div className="font-medium">Adult</div>
                  <div className="text-xs text-gray-500">Adult Fantasy</div>
                </button>
                <button
                  onClick={() => setPrefersYa(null)}
                  className={`p-4 rounded-lg border-2 text-center transition-colors ${
                    prefersYa === null
                      ? "border-purple-500 bg-purple-50"
                      : "border-gray-200 hover:border-purple-300"
                  }`}
                >
                  <div className="font-medium">Both</div>
                  <div className="text-xs text-gray-500">No preference</div>
                </button>
              </div>
            </div>

            <button
              onClick={handleSavePreferences}
              disabled={loading}
              className="w-full py-3 px-4 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50"
            >
              {loading ? "Saving..." : "Continue"}
            </button>
          </div>
        );

      case "rate-books":
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900">Rate Some Books</h2>
              <p className="mt-2 text-gray-600">
                Rate at least 5 books you&apos;ve read to get recommendations
              </p>
              <p className="text-sm text-purple-600 mt-1">
                {Object.keys(ratings).length} / 5 minimum
              </p>
            </div>

            {loading ? (
              <div className="text-center py-8">Loading books...</div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {starterBooks.map((book) => (
                  <div key={book.id} className="bg-white rounded-lg shadow p-3">
                    <div className="aspect-[2/3] bg-gray-100 rounded mb-2 flex items-center justify-center relative">
                      {book.cover_url ? (
                        <Image
                          src={book.cover_url}
                          alt={book.title}
                          fill
                          className="object-cover rounded"
                          sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
                        />
                      ) : (
                        <span className="text-3xl">📚</span>
                      )}
                    </div>
                    <h3 className="font-medium text-sm line-clamp-2">{book.title}</h3>
                    <p className="text-xs text-gray-500">{book.author}</p>

                    {/* Star rating */}
                    <div className="flex justify-center gap-1 mt-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => handleRateBook(book.id, star)}
                          className={`text-xl transition-colors ${
                            (ratings[book.id] || 0) >= star
                              ? "text-yellow-400"
                              : "text-gray-300 hover:text-yellow-300"
                          }`}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={handleSubmitRatings}
              disabled={loading || Object.keys(ratings).length < 5}
              className="w-full py-3 px-4 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Saving..." : "Get My Recommendations"}
            </button>
          </div>
        );

      case "complete":
        return (
          <div className="text-center space-y-6">
            <div className="text-6xl">🎉</div>
            <h2 className="text-2xl font-bold text-gray-900">You&apos;re All Set!</h2>
            <p className="text-gray-600">
              We&apos;ve got enough information to start recommending books for you.
            </p>
            <button
              onClick={() => router.push("/recommendations")}
              className="px-8 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700"
            >
              View My Recommendations
            </button>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Progress indicator */}
        <div className="flex items-center justify-center mb-8">
          {["import", "preferences", "rate-books", "complete"].map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === s
                    ? "bg-purple-600 text-white"
                    : ["import", "preferences", "rate-books", "complete"].indexOf(step) > i
                    ? "bg-purple-200 text-purple-700"
                    : "bg-gray-200 text-gray-500"
                }`}
              >
                {i + 1}
              </div>
              {i < 3 && (
                <div
                  className={`w-12 h-1 ${
                    ["import", "preferences", "rate-books", "complete"].indexOf(step) > i
                      ? "bg-purple-200"
                      : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Step content */}
        <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8">{renderStep()}</div>
      </div>
    </div>
  );
}
