import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ImageRecord, PaginatedHistoryResponse } from '../models/image.model';

@Injectable({
  providedIn: 'root'
})
export class ImageService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/api';

  getLatestImage(): Observable<ImageRecord> {
    return this.http.get<ImageRecord>(`${this.apiUrl}/image/latest`);
  }

  getHistory(page: number = 1, limit: number = 15): Observable<PaginatedHistoryResponse> {
    return this.http.get<PaginatedHistoryResponse>(`${this.apiUrl}/history?page=${page}&limit=${limit}`);
  }

  getHistoricalImage(imageId: string): Observable<ImageRecord> {
    return this.http.get<ImageRecord>(`${this.apiUrl}/history/${imageId}`);
  }
}
