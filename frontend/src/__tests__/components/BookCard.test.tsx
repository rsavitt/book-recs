import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BookCard } from "@/components/BookCard";
import type { BookSearchResult, Recommendation } from "@/types";

describe("BookCard", () => {
  const mockBook: BookSearchResult = {
    id: 1,
    title: "A Court of Thorns and Roses",
    author: "Sarah J. Maas",
    cover_url: "https://example.com/cover.jpg",
    publication_year: 2015,
    is_romantasy: true,
    series_name: "A Court of Thorns and Roses",
    series_position: 1,
  };

  const mockRecommendation: Recommendation = {
    book_id: 1,
    title: "Fourth Wing",
    author: "Rebecca Yarros",
    cover_url: null,
    publication_year: 2023,
    series_name: "The Empyrean",
    series_position: 1,
    spice_level: 4,
    is_ya: false,
    tags: ["enemies-to-lovers", "dragons", "academy"],
    predicted_rating: 4.6,
    confidence: 0.85,
    explanation: {
      similar_user_count: 12,
      average_neighbor_rating: 4.5,
      top_shared_books: ["ACOTAR", "From Blood and Ash"],
      sample_explanation: "12 similar readers rated this 4.5★ average",
    },
  };

  describe("with BookSearchResult", () => {
    it("renders book title and author", () => {
      render(<BookCard book={mockBook} />);

      expect(screen.getByText("A Court of Thorns and Roses")).toBeInTheDocument();
      expect(screen.getByText("Sarah J. Maas")).toBeInTheDocument();
    });

    it("renders series information", () => {
      render(<BookCard book={mockBook} />);

      expect(screen.getByText("A Court of Thorns and Roses #1")).toBeInTheDocument();
    });

    it("renders publication year", () => {
      render(<BookCard book={mockBook} />);

      expect(screen.getByText("2015")).toBeInTheDocument();
    });

    it("renders cover image when provided", () => {
      render(<BookCard book={mockBook} />);

      const img = screen.getByAltText("A Court of Thorns and Roses");
      expect(img).toBeInTheDocument();
    });

    it("renders placeholder when no cover", () => {
      const bookWithoutCover = { ...mockBook, cover_url: null };
      render(<BookCard book={bookWithoutCover} />);

      // Should show emoji placeholder
      expect(screen.getByText("📚")).toBeInTheDocument();
    });
  });

  describe("with Recommendation", () => {
    it("renders spice level", () => {
      render(<BookCard book={mockRecommendation} />);

      // Should show fire emojis for spice level 4
      expect(screen.getByText(/🔥/)).toBeInTheDocument();
    });

    it("renders tags", () => {
      render(<BookCard book={mockRecommendation} />);

      expect(screen.getByText("enemies-to-lovers")).toBeInTheDocument();
      expect(screen.getByText("dragons")).toBeInTheDocument();
    });

    it("shows explanation when showExplanation is true", () => {
      render(<BookCard book={mockRecommendation} showExplanation />);

      expect(screen.getByText(/12 similar readers/)).toBeInTheDocument();
    });
  });

  describe("feedback buttons", () => {
    it("renders feedback buttons when onFeedback provided", () => {
      const onFeedback = jest.fn();
      render(<BookCard book={mockBook} onFeedback={onFeedback} />);

      expect(screen.getByText("Want to Read")).toBeInTheDocument();
      expect(screen.getByText("Not Interested")).toBeInTheDocument();
    });

    it("calls onFeedback with 'interested' when Want to Read clicked", async () => {
      const user = userEvent.setup();
      const onFeedback = jest.fn();
      render(<BookCard book={mockBook} onFeedback={onFeedback} />);

      await user.click(screen.getByText("Want to Read"));

      expect(onFeedback).toHaveBeenCalledWith("interested");
    });

    it("calls onFeedback with 'not_interested' when Not Interested clicked", async () => {
      const user = userEvent.setup();
      const onFeedback = jest.fn();
      render(<BookCard book={mockBook} onFeedback={onFeedback} />);

      await user.click(screen.getByText("Not Interested"));

      expect(onFeedback).toHaveBeenCalledWith("not_interested");
    });

    it("does not render feedback buttons when onFeedback not provided", () => {
      render(<BookCard book={mockBook} />);

      expect(screen.queryByText("Want to Read")).not.toBeInTheDocument();
    });
  });
});
