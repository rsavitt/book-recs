import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecommendationCard } from "@/components/RecommendationCard";
import type { Recommendation } from "@/types";

describe("RecommendationCard", () => {
  const mockRecommendation: Recommendation = {
    book_id: 1,
    title: "Fourth Wing",
    author: "Rebecca Yarros",
    cover_url: "https://example.com/cover.jpg",
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

  it("renders book title and author", () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);

    expect(screen.getByText("Fourth Wing")).toBeInTheDocument();
    expect(screen.getByText("Rebecca Yarros")).toBeInTheDocument();
  });

  it("renders predicted rating badge", () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);

    expect(screen.getByText("4.6★")).toBeInTheDocument();
  });

  it("renders spice level badge for spicy books", () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);

    // Should show spice indicators
    const spiceBadge = screen.getByText(/🌶️/);
    expect(spiceBadge).toBeInTheDocument();
  });

  it("does not render spice badge for non-spicy books", () => {
    const cleanBook = { ...mockRecommendation, spice_level: 0 };
    render(<RecommendationCard recommendation={cleanBook} />);

    // Should not show spice indicators (except in any potential UI text)
    const container = screen.getByText("Fourth Wing").closest("div");
    expect(container?.textContent).not.toContain("🌶️");
  });

  it("renders series information", () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);

    expect(screen.getByText("The Empyrean #1")).toBeInTheDocument();
  });

  it("renders tags", () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);

    expect(screen.getByText("enemies-to-lovers")).toBeInTheDocument();
    expect(screen.getByText("dragons")).toBeInTheDocument();
  });

  it("limits visible tags", () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);

    // Should show +1 indicator for the third tag
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  describe("Why this book? button", () => {
    it("toggles explanation panel on click", async () => {
      const user = userEvent.setup();
      render(<RecommendationCard recommendation={mockRecommendation} />);

      // Initially, detailed explanation should not be visible
      expect(screen.queryByText(/You both loved:/)).not.toBeInTheDocument();

      // Click "Why this book?"
      await user.click(screen.getByText("Why this book?"));

      // Now explanation should be visible (use getAllByText since text appears in multiple places)
      expect(screen.getAllByText(/12 similar readers rated this/).length).toBeGreaterThan(0);
    });
  });

  describe("feedback buttons", () => {
    it("renders feedback buttons when onFeedback provided", () => {
      const onFeedback = jest.fn();
      render(
        <RecommendationCard
          recommendation={mockRecommendation}
          onFeedback={onFeedback}
        />
      );

      expect(screen.getByText("Want to Read")).toBeInTheDocument();
      expect(screen.getByText("Not for me")).toBeInTheDocument();
    });

    it("calls onFeedback and shows confirmation on click", async () => {
      const user = userEvent.setup();
      const onFeedback = jest.fn();
      render(
        <RecommendationCard
          recommendation={mockRecommendation}
          onFeedback={onFeedback}
        />
      );

      await user.click(screen.getByText("Want to Read"));

      expect(onFeedback).toHaveBeenCalledWith("interested");
      expect(screen.getByText(/Added to Want to Read/)).toBeInTheDocument();
    });

    it("shows dismissed confirmation for not interested", async () => {
      const user = userEvent.setup();
      const onFeedback = jest.fn();
      render(
        <RecommendationCard
          recommendation={mockRecommendation}
          onFeedback={onFeedback}
        />
      );

      await user.click(screen.getByText("Not for me"));

      expect(onFeedback).toHaveBeenCalledWith("not_interested");
      expect(screen.getByText(/Dismissed/)).toBeInTheDocument();
    });

    it("does not render feedback buttons when onFeedback not provided", () => {
      render(<RecommendationCard recommendation={mockRecommendation} />);

      expect(screen.queryByText("Want to Read")).not.toBeInTheDocument();
    });
  });

  describe("cover image", () => {
    it("renders cover image when provided", () => {
      render(<RecommendationCard recommendation={mockRecommendation} />);

      const img = screen.getByAltText("Fourth Wing");
      expect(img).toBeInTheDocument();
    });

    it("renders placeholder when no cover", () => {
      const noCover = { ...mockRecommendation, cover_url: null };
      render(<RecommendationCard recommendation={noCover} />);

      // RecommendationCard shows the book title as placeholder when no cover
      const placeholders = screen.getAllByText("Fourth Wing");
      expect(placeholders.length).toBeGreaterThan(1); // Title appears in both placeholder and card body
    });
  });
});
