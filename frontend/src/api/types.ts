/** Mirrors the API response schemas in backend/app/schemas. */

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Card {
  id: string;
  list_id: string;
  title: string;
  description: string | null;
  position: number;
  created_at: string;
  updated_at: string;
}

export interface BoardList {
  id: string;
  board_id: string;
  title: string;
  position: number;
  cards: Card[];
}

export interface Board {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface BoardDetail extends Board {
  lists: BoardList[];
}

export interface AuthResponse {
  user: User;
  access_token: string;
}

/** The single error envelope every non-2xx response uses. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: { field?: string };
  };
}
