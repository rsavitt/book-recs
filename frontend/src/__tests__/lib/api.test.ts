import { api } from "@/lib/api";

describe("ApiClient", () => {
  const mockFetch = global.fetch as jest.Mock;

  beforeEach(() => {
    mockFetch.mockClear();
    // Clear any stored token
    api.setToken(null);
  });

  describe("token management", () => {
    it("stores token in localStorage", () => {
      api.setToken("test-token");

      expect(localStorage.setItem).toHaveBeenCalledWith("auth_token", "test-token");
    });

    it("removes token from localStorage on logout", () => {
      api.logout();

      expect(localStorage.removeItem).toHaveBeenCalledWith("auth_token");
    });

    it("retrieves token from localStorage", () => {
      (localStorage.getItem as jest.Mock).mockReturnValue("stored-token");

      const token = api.getToken();

      expect(token).toBe("stored-token");
    });
  });

  describe("register", () => {
    it("sends registration request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 1,
            email: "test@example.com",
            username: "testuser",
          }),
      });

      const result = await api.register({
        email: "test@example.com",
        username: "testuser",
        password: "password123",
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/register"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            email: "test@example.com",
            username: "testuser",
            password: "password123",
          }),
        })
      );
      expect(result.email).toBe("test@example.com");
    });

    it("throws error on registration failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Email already registered" }),
      });

      await expect(
        api.register({
          email: "existing@example.com",
          username: "testuser",
          password: "password123",
        })
      ).rejects.toThrow("Email already registered");
    });
  });

  describe("login", () => {
    it("sends login request and stores token", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            access_token: "new-token",
            token_type: "bearer",
          }),
      });

      const result = await api.login({
        username: "test@example.com",
        password: "password123",
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/login"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        })
      );
      expect(result.access_token).toBe("new-token");
      expect(localStorage.setItem).toHaveBeenCalledWith("auth_token", "new-token");
    });

    it("throws error on login failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Invalid credentials" }),
      });

      await expect(
        api.login({
          username: "test@example.com",
          password: "wrongpassword",
        })
      ).rejects.toThrow("Invalid credentials");
    });
  });

  describe("getRecommendations", () => {
    beforeEach(() => {
      api.setToken("test-token");
    });

    it("fetches recommendations with filters", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve([
            {
              book_id: 1,
              title: "Test Book",
              predicted_rating: 4.5,
            },
          ]),
      });

      const result = await api.getRecommendations({
        spiceMin: 2,
        spiceMax: 4,
        isYa: false,
        tropes: ["enemies-to-lovers"],
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/recommendations\/\?.*spice_min=2.*spice_max=4.*is_ya=false.*tropes=enemies-to-lovers/),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
      expect(result).toHaveLength(1);
    });
  });

  describe("submitFeedback", () => {
    beforeEach(() => {
      api.setToken("test-token");
    });

    it("submits feedback for a book", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      await api.submitFeedback(1, "interested");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/recommendations/1/feedback?feedback=interested"),
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  describe("importGoodreads", () => {
    beforeEach(() => {
      api.setToken("test-token");
    });

    it("uploads CSV file", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            import_id: "abc123",
            status: "processing",
          }),
      });

      const file = new File(["csv content"], "export.csv", { type: "text/csv" });
      const result = await api.importGoodreads(file);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/imports/goodreads"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
      expect(result.import_id).toBe("abc123");
    });
  });

  describe("searchBooks", () => {
    it("searches books with query", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve([
            { id: 1, title: "Fourth Wing" },
            { id: 2, title: "Court of Thorns" },
          ]),
      });

      const result = await api.searchBooks("wing");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/books\/\?q=wing/),
        expect.anything()
      );
      expect(result).toHaveLength(2);
    });

    it("filters to romantasy only", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await api.searchBooks("test", true);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/romantasy_only=true/),
        expect.anything()
      );
    });
  });
});
