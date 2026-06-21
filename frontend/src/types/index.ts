export type Role = 'user' | 'librarian' | 'admin'

export interface User {
  id: number
  username: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface Category {
  id: number
  name: string
  created_at: string
}

export interface Edition {
  id: number
  name: string
  created_at: string
}

export interface Book {
  id: number
  title: string
  author: string
  category_id: number | null
  edition_id: number | null
  category: Category | null
  edition: Edition | null
  cover_image_id: number | null
  notes: string | null
  year: number | null
  created_by: number | null
  created_at: string
  updated_at: string
}

export interface BookImage {
  id: number
  book_id: number
  position: number
  content_type: string
  width: number | null
  height: number | null
  created_at: string
}

export interface WishList {
  id: number
  name: string
  is_public: boolean
  owner_id: number
  owner_username: string
  entry_count: number
  created_at: string
  updated_at: string
}

export interface WishListEntry {
  id: number
  wish_list_id: number
  title: string
  author: string
  category_id: number | null
  edition_id: number | null
  category: Category | null
  edition: Edition | null
  cover_image_id: number | null
  notes: string | null
  year: number | null
  created_at: string
  updated_at: string
}

export interface WishListEntryImage {
  id: number
  wish_list_entry_id: number
  position: number
  content_type: string
  width: number | null
  height: number | null
  created_at: string
}

export const ROLE_RANK: Record<Role, number> = {
  user: 0,
  librarian: 1,
  admin: 2,
}

export function roleAtLeast(role: Role, minRole: Role): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[minRole]
}
