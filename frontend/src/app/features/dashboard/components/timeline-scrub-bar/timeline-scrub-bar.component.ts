import { Component, input, output, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryItem } from '../../../../core/models/image.model';

@Component({
  selector: 'app-timeline-scrub-bar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './timeline-scrub-bar.component.html',
  styleUrls: ['./timeline-scrub-bar.component.css']
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

  // Divide timeline range into 5 visual ruler markers
  timeMarkers = computed(() => {
    const bounds = this.timeBounds();
    const list = this.sortedHistory();
    if (list.length === 0 || bounds.range === 0) return [];
    
    const count = 5;
    const markers = [];
    for (let i = 0; i < count; i++) {
      const ratio = i / (count - 1);
      const timestampMs = bounds.start + ratio * bounds.range;
      const date = new Date(timestampMs);
      
      // Format as HH:mm:ss
      const label = date.toTimeString().split(' ')[0];
      markers.push({ label, ratio });
    }
    return markers;
  });

  // Hover states
  hoveredItem = signal<HistoryItem | null>(null);
  tooltipX = signal<number | null>(null);
  hoverRatio = signal<number | null>(null); // Proportional X coordinate (0 to 1) for the red hover line

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
    const ratio = hoverX / width;
    this.hoverRatio.set(ratio);
    
    const bounds = this.timeBounds();
    if (bounds.range === 0) return;
    
    // Calculate targeted timestamp based on cursor position
    const targetTime = bounds.start + ratio * bounds.range;
    
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
    this.hoverRatio.set(null);
  }

  onClick(event: MouseEvent): void {
    if (this.hoveredItem()) {
      this.selectImage.emit(this.hoveredItem()!);
    }
  }
}
