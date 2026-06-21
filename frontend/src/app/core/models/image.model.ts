export interface ImageRecord {
  id: number;
  image_id: string;
  timestamp: string;
  raw_image_base64: string;
  processed_image_base64: string;
  intensity_average: number;
  focus_score: number;
  classification_label: string;
  histogram: number[];
}

export interface HistoryItem {
  id: number;
  image_id: string;
  timestamp: string;
  intensity_average: number;
  focus_score: number;
  classification_label: string;
}

export interface PaginatedHistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  limit: number;
}
