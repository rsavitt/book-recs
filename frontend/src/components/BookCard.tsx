"use client";

import Image from "next/image";
import type { BookSearchResult, Recommendation } from "@/types";

interface BookCardProps {
  book: BookSearchResult | Recommendation;
  showExplanation?: boolean;
  onFeedback?: (feedback: "interested" | "not_interested" | "already_read") => void;
}

export function BookCard({ book, showExplanation = false, onFeedback }: BookCardProps) {
  const isRecommendation = "predicted_rating" in book;
  const recommendation = isRecommendation ? (book as Recommendation) : null;

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      <div className="aspect-[2/3] relative bg-gray-100">
        {book.cover_url ? (
          <Image
            src={book.cover_url}
            alt={book.title}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 50vw, 200px"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400">
            <span className="text-4xl">📚</span>
          </div>
        )}
      </div>

      <div className="p-4">
        <h3 className="font-semibold text-gray-900 line-clamp-2" title={book.title}>
          {book.title}
        </h3>
        <p className="text-sm text-gray-600 mt-1">{book.author}</p>

        {book.series_name && (
          <p className="text-xs text-gray-500 mt-1">
            {book.series_name}
            {book.series_position && ` #${book.series_position}`}
          </p>
        )}

        {book.publication_year && (
          <p className="text-xs text-gray-400 mt-1">{book.publication_year}</p>
        )}

        {/* Recommendation-specific info */}
        {recommendation && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            {recommendation.spice_level !== null && (
              <div className="flex items-center gap-1 text-sm">
                <span>🌶️</span>
                <span className="text-gray-600">
                  {Array(recommendation.spice_level).fill("🔥").join("")}
                </span>
              </div>
            )}

            {recommendation.tags && recommendation.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {recommendation.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {showExplanation && recommendation.explanation && (
              <p className="text-xs text-gray-500 mt-2 italic">
                {recommendation.explanation.sample_explanation}
              </p>
            )}
          </div>
        )}

        {/* Feedback buttons */}
        {onFeedback && (
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => onFeedback("interested")}
              className="flex-1 py-1.5 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
            >
              Want to Read
            </button>
            <button
              onClick={() => onFeedback("not_interested")}
              className="flex-1 py-1.5 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
            >
              Not Interested
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
