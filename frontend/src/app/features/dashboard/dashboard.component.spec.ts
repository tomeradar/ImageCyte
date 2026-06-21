import { describe, it, expect, beforeEach, vi } from 'vitest';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { DashboardComponent } from './dashboard.component';
import { ImageService } from '../../core/services/image.service';
import { AuthService } from '../../core/services/auth.service';
import { of } from 'rxjs';
import { ImageRecord, PaginatedHistoryResponse } from '../../core/models/image.model';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let imageServiceMock: any;
  let authServiceMock: any;

  const mockLatestImage: ImageRecord = {
    id: 1,
    image_id: 'img_001',
    timestamp: '2026-06-21T10:00:00Z',
    raw_image_base64: 'raw_data',
    intensity_average: 85.5,
    focus_score: 0.94,
    classification_label: 'Healthy',
    histogram: [1, 2, 3],
    overlays: {}
  };

  const mockHistory: PaginatedHistoryResponse = {
    items: [
      {
        id: 1,
        image_id: 'img_001',
        timestamp: '2026-06-21T10:00:00Z',
        intensity_average: 85.5,
        focus_score: 0.94,
        classification_label: 'Healthy',
        thumbnail_base64: 'thumb_data'
      }
    ],
    total: 1,
    page: 1,
    limit: 100
  };

  beforeEach(async () => {
    imageServiceMock = {
      getLatestImage: vi.fn().mockReturnValue(of(mockLatestImage)),
      getHistory: vi.fn().mockReturnValue(of(mockHistory)),
      getHistoricalImage: vi.fn().mockReturnValue(of(mockLatestImage))
    };

    authServiceMock = {
      logout: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ImageService, useValue: imageServiceMock },
        { provide: AuthService, useValue: authServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    component.isLiveMode.set(false); // Prevent polling during tests
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with history list', () => {
    expect(component.historyList().length).toBe(1);
    expect(component.historyList()[0].image_id).toBe('img_001');
  });

  it('should load historical image when selectHistoryItem is triggered', () => {
    const item = mockHistory.items[0];
    component.selectHistoryItem(item);
    
    expect(imageServiceMock.getHistoricalImage).toHaveBeenCalledWith('img_001');
    expect(component.isLiveMode()).toBe(false);
  });

  it('should change timeframe filter and reload history', () => {
    component.onTimeframeChange('10m');
    expect(component.selectedTimeframe()).toBe('10m');
    expect(imageServiceMock.getHistory).toHaveBeenCalled();
  });

  it('should trigger logout when sign out is clicked', () => {
    component.logout();
    expect(authServiceMock.logout).toHaveBeenCalled();
  });
});
