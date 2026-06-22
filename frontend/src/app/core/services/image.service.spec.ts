import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ImageService } from './image.service';

describe('ImageService', () => {
  let service: ImageService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ImageService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(ImageService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should call GET /image/latest', () => {
    service.getLatestImage().subscribe();
    const req = httpMock.expectOne('http://localhost:8000/api/image/latest');
    expect(req.request.method).toBe('GET');
  });

  it('should pass parameters to GET /history', () => {
    service.getHistory(1, 10, '10m').subscribe();
    const req = httpMock.expectOne((r) => r.url.includes('/history'));
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('page')).toBe('1');
    expect(req.request.params.get('limit')).toBe('10');
    expect(req.request.params.get('timeframe')).toBe('10m');
  });

  it('should call GET /history/{id}', () => {
    service.getHistoricalImage('id-abc').subscribe();
    const req = httpMock.expectOne('http://localhost:8000/api/history/id-abc');
    expect(req.request.method).toBe('GET');
  });
});
