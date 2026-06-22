import { Component, ElementRef, ViewChild, effect, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-histogram',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './histogram.component.html',
  styleUrls: ['./histogram.component.css']
})
export class HistogramComponent {
  histogram = input<number[]>([]);

  @ViewChild('histogramCanvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  constructor() {
    effect(() => {
      const data = this.histogram();
      this.draw(data);
    });
  }

  private draw(histogram: number[]): void {
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
