"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import type { Recommendation } from "@/types";

interface RecommendationCardProps {
  recommendation: Recommendation;
  onFeedback?: (feedback: "interested" | "not_interested" | "already_read") => void;
}

export function RecommendationCard({ recommendation, onFeedback }: RecommendationCardProps) {
  const [showExplanation, setShowExplanation] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null);

  const handleFeedback = (
    e: React.MouseEvent,
    feedback: "interested" | "not_interested" | "already_read"
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setFeedbackGiven(feedback);
    onFeedback?.(feedback);
  };

  const toggleExplanation = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowExplanation(!showExplanation);
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow group relative">
      <Link href={`/book/${recommendation.book_id}`}>
        {/* Cover */}
        <div className="aspect-[2/3] relative bg-gray-100">
          {recommendation.cover_url ? (
            <Image
              src={recommendation.cover_url}
              alt={recommendation.title}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 50vw, 200px"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-gray-400">
              <span className="text-4xl">📚</span>
            </div>
          )}

          {/* Predicted rating badge */}
          <div className="absolute top-2 right-2 bg-purple-600 text-white px-2 py-1 rounded text-xs font-medium">
            {recommendation.predicted_rating.toFixed(1)}★
          </div>

          {/* Spice level badge */}
          {recommendation.spice_level !== null && recommendation.spice_level > 0 && (
            <div className="absolute top-2 left-2 bg-orange-500 text-white px-2 py-1 rounded text-xs">
              {"🌶️".repeat(Math.min(recommendation.spice_level, 3))}
              {recommendation.spice_level > 3 && "+"}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-3">
          <h3
            className="font-semibold text-gray-900 line-clamp-2 text-sm"
            title={recommendation.title}
          >
            {recommendation.title}
          </h3>
          <p className="text-xs text-gray-600 mt-1">{recommendation.author}</p>

          {recommendation.series_name && (
            <p className="text-xs text-gray-500 mt-1">
              {recommendation.series_name}
              {recommendation.series_position && ` #${recommendation.series_position}`}
            </p>
          )}

          {/* Tags */}
          {recommendation.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {recommendation.tags.slice(0, 2).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-xs rounded"
                >
                  {tag}
                </span>
              ))}
              {recommendation.tags.length > 2 && (
                <span className="px-1.5 py-0.5 text-gray-500 text-xs">
                  +{recommendation.tags.length - 2}
                </span>
              )}
            </div>
          )}

          {/* Why this book button */}
          <button
            onClick={toggleExplanation}
            className="mt-2 text-xs text-purple-600 hover:text-purple-500 flex items-center gap-1"
          >
            <span>Why this book?</span>
            <span>{showExplanation ? "▲" : "▼"}</span>
          </button>
        </div>
      </Link>

      {/* Explanation panel */}
      {showExplanation && (
        <div className="px-3 pb-3 border-t border-gray-100 mt-2 pt-2">
          <p className="text-xs text-gray-600 italic">
            {recommendation.explanation.sample_explanation}
          </p>
          <div className="mt-2 text-xs text-gray-500">
            <div>
              {recommendation.explanation.similar_user_count} similar readers rated this{" "}
              {recommendation.explanation.average_neighbor_rating.toFixed(1)}★ average
            </div>
            {recommendation.explanation.top_shared_books.length > 0 && (
              <div className="mt-1">
                You both loved: {recommendation.explanation.top_shared_books.slice(0, 2).join(", ")}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Feedback buttons */}
      {onFeedback && !feedbackGiven && (
        <div className="px-3 pb-3 flex gap-2">
          <button
            onClick={(e) => handleFeedback(e, "interested")}
            className="flex-1 py-1.5 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
          >
            Want to Read
          </button>
          <button
            onClick={(e) => handleFeedback(e, "not_interested")}
            className="flex-1 py-1.5 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
          >
            Not for me
          </button>
        </div>
      )}

      {/* Feedback confirmation */}
      {feedbackGiven && (
        <div className="px-3 pb-3">
          <div className="text-xs text-center py-1.5 bg-gray-50 rounded text-gray-600">
            {feedbackGiven === "interested" && "✓ Added to Want to Read"}
            {feedbackGiven === "not_interested" && "✓ Dismissed"}
            {feedbackGiven === "already_read" && "✓ Marked as read"}
          </div>
        </div>
      )}
    </div>
  );
}
