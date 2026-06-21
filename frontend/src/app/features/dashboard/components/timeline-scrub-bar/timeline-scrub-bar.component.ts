import { Component, input, output, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryItem } from '../../../../core/models/image.model';

@Component({
  selector: 'app-timeline-scrub-bar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <footer class="timeline-container">
      <div class="timeline-header">
        <div class="header-info">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" class="icon-spacing">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <span class="timeline-title">Scrub Ingestion History</span>
        </div>
        <span class="timeline-count" *ngIf="historyList().length">
          {{ historyList().length }} frames cached
        </span>
      </div>

      <div class="timeline-body">
        <div *ngIf="historyList().length === 0" class="timeline-empty">
          No records cached in this timeframe.
        </div>

        <div 
          *ngIf="historyList().length > 0"
          class="track-wrapper"
          (mousemove)="onMouseMove($event)"
          (mouseleave)="onMouseLeave()"
          (click)="onClick($event)"
          #trackContainer
        >
          <!-- The visual scrubbing track line -->
          <div class="track-bar">
            <!-- Selected Image indicator line -->
            <div 
              *ngIf="selectedRatio() !== null"
              class="selected-progress"
              [style.width.%]="selectedRatio()! * 100"
            ></div>

            <!-- Tick markers for each historical frame -->
            <div 
              *ngFor="let item of sortedHistory()"
              class="timeline-tick"
              [class.active]="currentImageId() === item.image_id"
              [style.left.%]="getRatio(item) * 100"
            ></div>
          </div>

          <!-- The Floating YouTube-style Tooltip Preview -->
          <div 
            *ngIf="hoveredItem() && tooltipX() !== null"
            class="scrub-tooltip"
            [style.left.px]="tooltipX()"
          >
            <div class="tooltip-arrow"></div>
            
            <div class="tooltip-thumbnail">
              <img 
                *ngIf="hoveredItem()?.thumbnail_base64"
                [src]="'data:image/png;base64,' + hoveredItem()?.thumbnail_base64" 
                alt="Thumbnail"
              />
              <div *ngIf="!hoveredItem()?.thumbnail_base64" class="no-thumbnail">No Preview</div>
            </div>

            <div class="tooltip-meta">
              <div class="tooltip-row header">
                <span class="tooltip-id">{{ hoveredItem()?.image_id }}</span>
                <span 
                  class="tooltip-badge" 
                  [class.badge-healthy]="hoveredItem()?.classification_label === 'Healthy'"
                  [class.badge-warning]="hoveredItem()?.classification_label !== 'Healthy'"
                >
                  {{ hoveredItem()?.classification_label }}
                </span>
              </div>
              <div class="tooltip-row details">
                <span>Int: {{ hoveredItem()?.intensity_average?.toFixed(1) }}</span>
                <span>Focus: {{ hoveredItem()?.focus_score?.toFixed(2) }}</span>
              </div>
              <div class="tooltip-time">
                {{ hoveredItem()?.timestamp | date:'HH:mm:ss (MM/dd)' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  `,
  styles: [`
    .timeline-container {
      background: rgba(17, 24, 39, 0.95);
      backdrop-filter: blur(12px);
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      display: flex;
      flex-direction: column;
      height: 140px;
      box-sizing: border-box;
      padding: 10px 24px;
    }
    .timeline-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .header-info {
      display: flex;
      align-items: center;
      color: #9ca3af;
      gap: 6px;
    }
    .icon-spacing {
      color: #00ffc8;
    }
    .timeline-title {
      font-family: 'Outfit', sans-serif;
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #ffffff;
    }
    .timeline-count {
      font-size: 0.75rem;
      color: #00ffc8;
      background: rgba(0, 255, 200, 0.08);
      padding: 2px 8px;
      border-radius: 12px;
      border: 1px solid rgba(0, 255, 200, 0.15);
    }
    .timeline-body {
      flex: 1;
      display: flex;
      align-items: center;
      position: relative;
    }
    .timeline-empty {
      width: 100%;
      text-align: center;
      color: #6b7280;
      font-size: 0.85rem;
    }
    .track-wrapper {
      position: relative;
      width: 100%;
      height: 36px;
      display: flex;
      align-items: center;
      cursor: pointer;
    }
    .track-bar {
      width: 100%;
      height: 6px;
      background: #1f2937;
      border-radius: 4px;
      position: relative;
      transition: height 0.15s ease;
    }
    .track-wrapper:hover .track-bar {
      height: 8px;
    }
    .selected-progress {
      height: 100%;
      background: linear-gradient(90deg, #009f7a, #00ffc8);
      border-radius: 4px;
      position: absolute;
      left: 0;
      top: 0;
      pointer-events: none;
    }
    .timeline-tick {
      position: absolute;
      width: 6px;
      height: 6px;
      background: #4b5563;
      border-radius: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
      transition: all 0.2s ease;
    }
    .track-wrapper:hover .timeline-tick {
      width: 8px;
      height: 8px;
    }
    .timeline-tick.active {
      background: #00ffc8;
      box-shadow: 0 0 8px #00ffc8;
      z-index: 2;
    }
    /* Floating Tooltip */
    .scrub-tooltip {
      position: absolute;
      bottom: calc(100% + 14px);
      width: 240px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(0, 255, 200, 0.2);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      border-radius: 8px;
      padding: 8px;
      display: flex;
      gap: 10px;
      transform: translateX(-50%);
      pointer-events: none;
      z-index: 100;
      animation: fadeIn 0.1s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translate(-50%, 5px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }
    .tooltip-arrow {
      position: absolute;
      bottom: -6px;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-top: 6px solid rgba(15, 23, 42, 0.95);
    }
    .tooltip-thumbnail {
      width: 80px;
      height: 60px;
      border-radius: 4px;
      overflow: hidden;
      background: #000;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .tooltip-thumbnail img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .no-thumbnail {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.6rem;
      color: #4b5563;
    }
    .tooltip-meta {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-width: 0;
    }
    .tooltip-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
    }
    .tooltip-row.header {
      margin-bottom: 2px;
    }
    .tooltip-id {
      font-family: monospace;
      font-size: 0.75rem;
      font-weight: 700;
      color: #ffffff;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .tooltip-badge {
      font-size: 0.6rem;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .badge-healthy {
      background: rgba(16, 185, 129, 0.1);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .badge-warning {
      background: rgba(245, 158, 11, 0.1);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.2);
    }
    .tooltip-row.details {
      font-size: 0.65rem;
      color: #9ca3af;
      margin-bottom: 2px;
    }
    .tooltip-time {
      font-size: 0.6rem;
      color: #6b7280;
    }
  `]
})
export class TimelineScrubBarComponent {
  historyList = input<HistoryItem[]>([]);
  currentImageId = input<string | null>(null);
  selectImage = output<HistoryItem>();

  // Chronologically sorted items: Oldest to Newest
  sortedHistory = computed(() => {
    return [...this.historyList()].reverse();
  });

  // Oldest & Newest timestamp bounds
  timeBounds = computed(() => {
    const list = this.sortedHistory();
    if (list.length === 0) return { start: 0, end: 0, range: 0 };
    const start = new Date(list[0].timestamp).getTime();
    const end = new Date(list[list.length - 1].timestamp).getTime();
    return { start, end, range: end - start };
  });

  // Calculate ratio of current image along the timeline
  selectedRatio = computed(() => {
    const currentId = this.currentImageId();
    const list = this.sortedHistory();
    const bounds = this.timeBounds();
    if (!currentId || list.length === 0 || bounds.range === 0) return null;
    
    const current = list.find(item => item.image_id === currentId);
    if (!current) return null;
    
    const currTime = new Date(current.timestamp).getTime();
    return (currTime - bounds.start) / bounds.range;
  });

  // Hover states
  hoveredItem = signal<HistoryItem | null>(null);
  tooltipX = signal<number | null>(null);

  getRatio(item: HistoryItem): number {
    const bounds = this.timeBounds();
    if (bounds.range === 0) return 0.5;
    const itemTime = new Date(item.timestamp).getTime();
    return (itemTime - bounds.start) / bounds.range;
  }

  onMouseMove(event: MouseEvent): void {
    const container = event.currentTarget as HTMLElement;
    const rect = container.getBoundingClientRect();
    const width = rect.width;
    
    // Clamp hover x inside track bounds
    const hoverX = Math.max(0, Math.min(event.clientX - rect.left, width));
    
    const bounds = this.timeBounds();
    if (bounds.range === 0) return;
    
    // Calculate targeted timestamp based on cursor position
    const targetTime = bounds.start + (hoverX / width) * bounds.range;
    
    // Find closest frame to the cursor target timestamp
    const list = this.sortedHistory();
    let closestItem: HistoryItem | null = null;
    let minDiff = Infinity;
    
    for (const item of list) {
      const itemTime = new Date(item.timestamp).getTime();
      const diff = Math.abs(itemTime - targetTime);
      if (diff < minDiff) {
        minDiff = diff;
        closestItem = item;
      }
    }
    
    this.hoveredItem.set(closestItem);
    this.tooltipX.set(hoverX);
  }

  onMouseLeave(): void {
    this.hoveredItem.set(null);
    this.tooltipX.set(null);
  }

  onClick(event: MouseEvent): void {
    if (this.hoveredItem()) {
      this.selectImage.emit(this.hoveredItem()!);
    }
  }
}
