import { Component, OnInit, OnDestroy, ViewChild, ElementRef, inject, AfterViewInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ImageService } from '../../core/services/image.service';
import { AuthService } from '../../core/services/auth.service';
import { ImageRecord, HistoryItem } from '../../core/models/image.model';
import { Subject, Subscription, timer } from 'rxjs';
import { takeUntil, switchMap, catchError } from 'rxjs/operators';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, OnDestroy, AfterViewInit {
  private imageService = inject(ImageService);
  private authService = inject(AuthService);

  @ViewChild('histogramCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  // Reactive state signals to trigger UI updates in Zoneless mode
  currentImage = signal<ImageRecord | null>(null);
  historyList = signal<HistoryItem[]>([]);
  
  isLiveMode = signal<boolean>(true);
  showProcessed = signal<boolean>(false);
  
  isLoading = signal<boolean>(true);
  isHistoryLoading = signal<boolean>(false);
  hasError = signal<boolean>(false);
  errorMessage = signal<string>('');

  private destroy$ = new Subject<void>();
  private pollSubscription: Subscription | null = null;

  ngOnInit(): void {
    this.startLiveStream();
    this.loadHistory();
  }

  ngAfterViewInit(): void {
    const img = this.currentImage();
    if (img) {
      this.drawHistogram(img.histogram);
    }
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
          setTimeout(() => this.drawHistogram(record.histogram), 0);
          this.loadHistory(); // Sync history list
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
    this.imageService.getHistory(1, 15).pipe(takeUntil(this.destroy$)).subscribe({
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

  selectHistoryItem(item: HistoryItem): void {
    this.isLiveMode.set(false);
    this.stopLiveStream();
    this.isLoading.set(true);
    this.hasError.set(false);

    this.imageService.getHistoricalImage(item.image_id).pipe(takeUntil(this.destroy$)).subscribe({
      next: (record) => {
        this.currentImage.set(record);
        this.isLoading.set(false);
        setTimeout(() => this.drawHistogram(record.histogram), 0);
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

  toggleOverlay(): void {
    this.showProcessed.set(!this.showProcessed());
  }

  logout(): void {
    this.authService.logout();
  }

  drawHistogram(histogram: number[]): void {
    if (!this.canvasRef || !histogram || histogram.length === 0) return;
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const maxVal = Math.max(...histogram, 1);
    const barWidth = width / histogram.length;

    const grad = ctx.createLinearGradient(0, height, 0, 0);
    grad.addColorStop(0, '#009f7a');
    grad.addColorStop(0.5, '#00ffc8');
    grad.addColorStop(1, '#a7f3d0');

    for (let i = 0; i < histogram.length; i++) {
      const val = histogram[i];
      const barHeight = (val / maxVal) * (height - 15);
      const x = i * barWidth;
      const y = height - barHeight;

      ctx.fillStyle = grad;
      ctx.fillRect(x, y, barWidth - 0.2, barHeight);
    }

    ctx.fillStyle = '#6b7280';
    ctx.font = '8px Inter';
    ctx.fillText('0 (Low)', 2, height - 2);
    ctx.fillText('128 (Mid)', width / 2 - 18, height - 2);
    ctx.fillText('255 (High)', width - 42, height - 2);
  }
}
