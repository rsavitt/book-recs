import type {
  User,
  UserProfile,
  SimilarUser,
  Book,
  BookSearchResult,
  BookTag,
  Recommendation,
  ImportStatus,
  LoginCredentials,
  RegisterData,
  AuthToken,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("auth_token", token);
      } else {
        localStorage.removeItem("auth_token");
      }
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("auth_token");
    }
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const token = this.getToken();

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "An error occurred" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints
  async register(data: RegisterData): Promise<User> {
    return this.request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async login(credentials: LoginCredentials): Promise<AuthToken> {
    const formData = new URLSearchParams();
    formData.append("username", credentials.username);
    formData.append("password", credentials.password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(error.detail);
    }

    const token = await response.json();
    this.setToken(token.access_token);
    return token;
  }

  logout() {
    this.setToken(null);
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>("/auth/me");
  }

  // User endpoints
  async getProfile(): Promise<UserProfile> {
    return this.request<UserProfile>("/users/profile");
  }

  async updatePreferences(preferences: Partial<User>): Promise<void> {
    await this.request("/users/preferences", {
      method: "PATCH",
      body: JSON.stringify(preferences),
    });
  }

  async getSimilarUsers(limit = 20): Promise<SimilarUser[]> {
    return this.request<SimilarUser[]>(`/users/neighbors?limit=${limit}`);
  }

  // Book endpoints
  async searchBooks(query: string, romantasyOnly = false): Promise<BookSearchResult[]> {
    return this.request<BookSearchResult[]>(
      `/books/?q=${encodeURIComponent(query)}&romantasy_only=${romantasyOnly}`
    );
  }

  async getBook(id: number): Promise<Book> {
    return this.request<Book>(`/books/${id}`);
  }

  async listRomantasyBooks(params: {
    spiceLevel?: number;
    isYa?: boolean;
    tropes?: string[];
    limit?: number;
    offset?: number;
  } = {}): Promise<BookSearchResult[]> {
    const searchParams = new URLSearchParams();
    if (params.spiceLevel !== undefined) searchParams.append("spice_level", String(params.spiceLevel));
    if (params.isYa !== undefined) searchParams.append("is_ya", String(params.isYa));
    if (params.tropes) params.tropes.forEach(t => searchParams.append("tropes", t));
    if (params.limit) searchParams.append("limit", String(params.limit));
    if (params.offset) searchParams.append("offset", String(params.offset));

    return this.request<BookSearchResult[]>(`/books/romantasy?${searchParams}`);
  }

  async getTags(category?: string): Promise<BookTag[]> {
    const params = category ? `?category=${category}` : "";
    return this.request<BookTag[]>(`/books/tags${params}`);
  }

  // Import endpoints
  async importGoodreads(file: File): Promise<ImportStatus> {
    const formData = new FormData();
    formData.append("file", file);

    const token = this.getToken();
    const response = await fetch(`${API_BASE_URL}/imports/goodreads`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Import failed" }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  async getImportStatus(importId: string): Promise<ImportStatus> {
    return this.request<ImportStatus>(`/imports/status/${importId}`);
  }

  // Recommendation endpoints
  async getRecommendations(params: {
    spiceMin?: number;
    spiceMax?: number;
    isYa?: boolean;
    tropes?: string[];
    excludeTropes?: string[];
    limit?: number;
    offset?: number;
  } = {}): Promise<Recommendation[]> {
    const searchParams = new URLSearchParams();
    if (params.spiceMin !== undefined) searchParams.append("spice_min", String(params.spiceMin));
    if (params.spiceMax !== undefined) searchParams.append("spice_max", String(params.spiceMax));
    if (params.isYa !== undefined) searchParams.append("is_ya", String(params.isYa));
    if (params.tropes) params.tropes.forEach(t => searchParams.append("tropes", t));
    if (params.excludeTropes) params.excludeTropes.forEach(t => searchParams.append("exclude_tropes", t));
    if (params.limit) searchParams.append("limit", String(params.limit));
    if (params.offset) searchParams.append("offset", String(params.offset));

    return this.request<Recommendation[]>(`/recommendations/?${searchParams}`);
  }

  async submitFeedback(bookId: number, feedback: "interested" | "not_interested" | "already_read"): Promise<void> {
    await this.request(`/recommendations/${bookId}/feedback?feedback=${feedback}`, {
      method: "POST",
    });
  }
}

export const api = new ApiClient();
