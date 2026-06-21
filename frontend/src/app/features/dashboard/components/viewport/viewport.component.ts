import { Component, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ImageRecord } from '../../../../core/models/image.model';

@Component({
  selector: 'app-viewport',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './viewport.component.html',
  styleUrls: ['./viewport.component.css']
})
export class ViewportComponent {
  currentImage = input<ImageRecord | null>(null);
  isLoading = input<boolean>(false);
  hasError = input<boolean>(false);
  errorMessage = input<string>('');

  selectedOverlays = signal<string[]>([]);

  toggleOverlay(type: string): void {
    const current = this.selectedOverlays();
    if (current.includes(type)) {
      this.selectedOverlays.set(current.filter(t => t !== type));
    } else {
      this.selectedOverlays.set([...current, type]);
    }
  }
}
