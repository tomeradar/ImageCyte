import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ImageService } from '../../core/services/image.service';
import { AuthService } from '../../core/services/auth.service';
import { ImageRecord, HistoryItem } from '../../core/models/image.model';
import { Subject, Subscription, timer } from 'rxjs';
import { takeUntil, switchMap, catchError } from 'rxjs/operators';

// Import subcomponents
import { ViewportComponent } from './components/viewport/viewport.component';
import { TimelineScrubBarComponent } from './components/timeline-scrub-bar/timeline-scrub-bar.component';
import { HistogramComponent } from './components/histogram/histogram.component';
import { MetricsComponent } from './components/metrics/metrics.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ViewportComponent,
    TimelineScrubBarComponent,
    HistogramComponent,
    MetricsComponent
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  private imageService = inject(ImageService);
  private authService = inject(AuthService);

  // Reactive state signals to trigger UI updates in Zoneless mode
  currentImage = signal<ImageRecord | null>(null);
  historyList = signal<HistoryItem[]>([]);
  
  isLiveMode = signal<boolean>(true);
  
  isLoading = signal<boolean>(true);
  isHistoryLoading = signal<boolean>(false);
  hasError = signal<boolean>(false);
  errorMessage = signal<string>('');

  // Timeframe states
  selectedTimeframe = signal<string>('all'); // all, 10m, 30m, 1h, 1d, custom
  customStart = signal<string>('');
  customEnd = signal<string>('');

  private destroy$ = new Subject<void>();
  private pollSubscription: Subscription | null = null;

  ngOnInit(): void {
    this.startLiveStream();
    this.loadHistory();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.stopLiveStream();
  }

  startLiveStream(): void {
    this.isLiveMode.set(true);
    this.stopLiveStream();

    this.pollSubscription = timer(0, 3000).pipe(
      switchMap(() => {
        if (!this.isLiveMode()) return [];
        return this.imageService.getLatestImage().pipe(
          catchError(err => {
            console.error('Error fetching latest image from backend:', err);
            this.hasError.set(true);
            this.errorMessage.set('Gateway proxy backend unreachable. Attempting to reconnect...');
            return [];
          })
        );
      }),
      takeUntil(this.destroy$)
    ).subscribe({
      next: (record: ImageRecord) => {
        this.hasError.set(false);
        this.isLoading.set(false);
        
        const current = this.currentImage();
        if (!current || current.image_id !== record.image_id) {
          this.currentImage.set(record);
          this.loadHistory(); // Sync timeline history list
        }
      }
    });
  }

  stopLiveStream(): void {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
      this.pollSubscription = null;
    }
  }

  loadHistory(): void {
    this.isHistoryLoading.set(true);
    const tf = this.selectedTimeframe();
    
    let startIso: string | undefined = undefined;
    let endIso: string | undefined = undefined;
    
    if (tf === 'custom') {
      if (this.customStart()) {
        startIso = new Date(this.customStart()).toISOString();
      }
      if (this.customEnd()) {
        endIso = new Date(this.customEnd()).toISOString();
      }
    }

    // Retrieve up to 100 items chronologically for the timeline track
    this.imageService.getHistory(
      1,
      100,
      tf !== 'all' ? tf : undefined,
      startIso,
      endIso
    ).pipe(takeUntil(this.destroy$)).subscribe({
      next: (res) => {
        this.historyList.set(res.items);
        this.isHistoryLoading.set(false);
      },
      error: (err) => {
        console.error('Error fetching history:', err);
        this.isHistoryLoading.set(false);
      }
    });
  }

  onTimeframeChange(tf: string): void {
    this.selectedTimeframe.set(tf);
    if (tf !== 'custom') {
      this.loadHistory();
    }
  }

  applyCustomFilter(): void {
    this.loadHistory();
  }

  selectHistoryItem(item: HistoryItem): void {
    this.isLiveMode.set(false);
    this.stopLiveStream();
    this.isLoading.set(true);
    this.hasError.set(false);

    this.imageService.getHistoricalImage(item.image_id).pipe(takeUntil(this.destroy$)).subscribe({
      next: (record) => {
        this.currentImage.set(record);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.hasError.set(true);
        this.errorMessage.set(`Failed to load historical scan ${item.image_id}.`);
      }
    });
  }

  resumeLive(): void {
    this.isLoading.set(true);
    this.startLiveStream();
  }

  logout(): void {
    this.authService.logout();
  }
}
