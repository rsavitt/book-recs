import { render, screen } from "@testing-library/react";
import { Header } from "@/components/Header";
import { api } from "@/lib/api";

// Mock the api module
jest.mock("@/lib/api", () => ({
  api: {
    getToken: jest.fn(),
  },
}));

describe("Header", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("when user is not logged in", () => {
    beforeEach(() => {
      (api.getToken as jest.Mock).mockReturnValue(null);
    });

    it("renders the logo", () => {
      render(<Header />);

      expect(screen.getByText("📚")).toBeInTheDocument();
      expect(screen.getByText("Romantasy Recs")).toBeInTheDocument();
    });

    it("renders login link", () => {
      render(<Header />);

      expect(screen.getByText("Log in")).toBeInTheDocument();
    });

    it("renders get started button", () => {
      render(<Header />);

      expect(screen.getByText("Get Started")).toBeInTheDocument();
    });

    it("renders browse link", () => {
      render(<Header />);

      expect(screen.getByText("Browse")).toBeInTheDocument();
    });

    it("does not render authenticated nav items", () => {
      render(<Header />);

      expect(screen.queryByText("My Recs")).not.toBeInTheDocument();
      expect(screen.queryByText("Profile")).not.toBeInTheDocument();
    });
  });

  describe("when user is logged in", () => {
    beforeEach(() => {
      (api.getToken as jest.Mock).mockReturnValue("mock-token");
    });

    it("renders authenticated nav items", () => {
      render(<Header />);

      expect(screen.getByText("My Recs")).toBeInTheDocument();
      expect(screen.getByText("Similar Readers")).toBeInTheDocument();
      expect(screen.getByText("Profile")).toBeInTheDocument();
    });

    it("does not render login/signup buttons", () => {
      render(<Header />);

      expect(screen.queryByText("Log in")).not.toBeInTheDocument();
      expect(screen.queryByText("Get Started")).not.toBeInTheDocument();
    });
  });

  describe("showAuthButtons prop", () => {
    it("hides auth buttons when showAuthButtons is false", () => {
      (api.getToken as jest.Mock).mockReturnValue(null);
      render(<Header showAuthButtons={false} />);

      expect(screen.queryByText("Log in")).not.toBeInTheDocument();
      expect(screen.queryByText("Get Started")).not.toBeInTheDocument();
    });
  });
});
