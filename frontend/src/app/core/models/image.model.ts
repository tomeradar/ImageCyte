export interface ImageRecord {
  id: number;
  image_id: string;
  timestamp: string;
  raw_image_base64: string;
  intensity_average: number;
  focus_score: number;
  classification_label: string;
  histogram: number[];
  overlays: { [key: string]: string }; // Map process type (canny, otsu) to base64 overlay mask
}

export interface HistoryItem {
  id: number;
  image_id: string;
  timestamp: string;
  intensity_average: number;
  focus_score: number;
  classification_label: string;
  thumbnail_base64: string; // Resized thumbnail for preview tooltip
}

export interface PaginatedHistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  limit: number;
}
