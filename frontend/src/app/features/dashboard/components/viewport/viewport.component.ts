import { Component, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ImageRecord } from '../../../../core/models/image.model';

@Component({
  selector: 'app-viewport',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="viewport-panel">
      <div class="panel-header">
        <h2>Microscope Feed</h2>
        <div class="overlay-selectors" *ngIf="currentImage()">
          <span class="selector-title">CV Overlays:</span>
          <button 
            [class.active]="selectedOverlays().includes('canny')"
            (click)="toggleOverlay('canny')"
            class="btn-overlay-toggle"
          >
            Canny Edges
          </button>
          <button 
            [class.active]="selectedOverlays().includes('otsu')"
            (click)="toggleOverlay('otsu')"
            class="btn-overlay-toggle"
          >
            Otsu Cells
          </button>
        </div>
      </div>

      <div class="viewport-content">
        <!-- Error Boundary State -->
        <div *ngIf="hasError()" class="viewport-message error-state">
          <svg viewBox="0 0 24 24" width="48" height="48" stroke="currentColor" stroke-width="2" fill="none" class="message-icon">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <h3>Connection Error</h3>
          <p>{{ errorMessage() }}</p>
        </div>

        <!-- Loading state -->
        <div *ngIf="isLoading() && !hasError()" class="viewport-message loading-state">
          <div class="loading-spinner"></div>
          <h3>Connecting Stream...</h3>
          <p>Downloading latest microscopy frame data</p>
        </div>

        <!-- Render Stream and Overlays -->
        <div *ngIf="!isLoading() && !hasError() && currentImage()" class="image-wrapper">
          <img 
            [src]="'data:image/png;base64,' + currentImage()?.raw_image_base64" 
            [alt]="'Microscopy frame ' + currentImage()?.image_id"
            class="microscope-img base-image"
          />
          <!-- Canny transparent overlay mask -->
          <img 
            *ngIf="selectedOverlays().includes('canny') && currentImage()?.overlays?.['canny']"
            [src]="'data:image/png;base64,' + currentImage()?.overlays?.['canny']"
            class="overlay-image canny-layer"
          />
          <!-- Otsu transparent overlay mask -->
          <img 
            *ngIf="selectedOverlays().includes('otsu') && currentImage()?.overlays?.['otsu']"
            [src]="'data:image/png;base64,' + currentImage()?.overlays?.['otsu']"
            class="overlay-image otsu-layer"
          />
        </div>
      </div>
    </section>
  `,
  styles: [`
    .viewport-panel {
      display: flex;
      flex-direction: column;
      background: #0e1322;
      border-right: 1px solid rgba(255, 255, 255, 0.05);
      height: 100%;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .panel-header h2 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.15rem;
      margin: 0;
      font-weight: 600;
      color: #ffffff;
    }
    .overlay-selectors {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .selector-title {
      font-size: 0.75rem;
      color: #6b7280;
      margin-right: 4px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .btn-overlay-toggle {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #d1d5db;
      font-family: 'Outfit', sans-serif;
      font-size: 0.8rem;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .btn-overlay-toggle:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
    }
    .btn-overlay-toggle.active {
      background: rgba(0, 255, 200, 0.1);
      border-color: #00ffc8;
      color: #00ffc8;
      box-shadow: 0 0 10px rgba(0, 255, 200, 0.15);
    }
    .viewport-content {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 24px;
      position: relative;
      overflow: hidden;
      background: #030712;
    }
    .image-wrapper {
      position: relative;
      max-width: 100%;
      max-height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.05);
      background: #000000;
    }
    .microscope-img {
      max-width: 100%;
      max-height: calc(100vh - 320px);
      object-fit: contain;
      display: block;
    }
    .overlay-image {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: contain;
      pointer-events: none;
      mix-blend-mode: screen; /* Blends overlays beautifully */
    }
    .viewport-message {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      color: #9ca3af;
      gap: 12px;
    }
    .message-icon {
      color: #ef4444;
    }
    .viewport-message h3 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.2rem;
      margin: 0;
      color: #ffffff;
    }
    .viewport-message p {
      font-size: 0.85rem;
      margin: 0;
    }
    .loading-spinner {
      width: 48px;
      height: 48px;
      border: 4px solid rgba(0, 255, 200, 0.1);
      border-top-color: #00ffc8;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      box-shadow: 0 0 15px rgba(0, 255, 200, 0.1);
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
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
