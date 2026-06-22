import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
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

  getHistory(
    page: number = 1,
    limit: number = 15,
    timeframe?: string,
    startTime?: string,
    endTime?: string
  ): Observable<PaginatedHistoryResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (timeframe) {
      params = params.set('timeframe', timeframe);
    }
    if (startTime) {
      params = params.set('start_time', startTime);
    }
    if (endTime) {
      params = params.set('end_time', endTime);
    }

    return this.http.get<PaginatedHistoryResponse>(`${this.apiUrl}/history`, { params });
  }

  getHistoricalImage(imageId: string): Observable<ImageRecord> {
    return this.http.get<ImageRecord>(`${this.apiUrl}/history/${imageId}`);
  }
}
