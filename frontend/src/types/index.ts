// User types
export interface User {
  id: number;
  email: string;
  username: string;
  display_name: string | null;
  is_public: boolean;
  spice_preference: number | null;
  prefers_ya: boolean | null;
}

export interface UserProfile extends User {
  bio: string | null;
  created_at: string;
  last_import_at: string | null;
  stats: RatingStats;
  top_shelves: string[];
}

export interface RatingStats {
  total_books: number;
  total_rated: number;
  average_rating: number;
  rating_distribution: Record<number, number>;
}

export interface SimilarUser {
  username: string;
  display_name: string | null;
  similarity_score: number;
  overlap_count: number;
  shared_favorites: string[];
}

// Book types
export interface Book {
  id: number;
  title: string;
  author: string;
  description: string | null;
  cover_url: string | null;
  page_count: number | null;
  publication_year: number | null;
  series_name: string | null;
  series_position: number | null;
  is_romantasy: boolean;
  spice_level: number | null;
  is_ya: boolean | null;
  tags: BookTag[];
  isbn_13: string | null;
  open_library_id: string | null;
}

export interface BookSearchResult {
  id: number;
  title: string;
  author: string;
  cover_url: string | null;
  publication_year: number | null;
  is_romantasy: boolean;
  series_name: string | null;
  series_position: number | null;
}

export interface BookTag {
  id: number;
  name: string;
  slug: string;
  category: string;
}

// Recommendation types
export interface Recommendation {
  book_id: number;
  title: string;
  author: string;
  cover_url: string | null;
  publication_year: number | null;
  series_name: string | null;
  series_position: number | null;
  spice_level: number | null;
  is_ya: boolean | null;
  tags: string[];
  predicted_rating: number;
  confidence: number;
  explanation: RecommendationExplanation;
}

export interface RecommendationExplanation {
  similar_user_count: number;
  average_neighbor_rating: number;
  top_shared_books: string[];
  sample_explanation: string;
}

// Import types
export interface ImportStatus {
  import_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  message: string | null;
  progress: number | null;
  books_processed: number | null;
  books_total: number | null;
  errors: string[] | null;
}

// Auth types
export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  display_name?: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
