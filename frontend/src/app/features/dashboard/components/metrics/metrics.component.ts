import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ImageRecord } from '../../../../core/models/image.model';

@Component({
  selector: 'app-metrics',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './metrics.component.html',
  styleUrls: ['./metrics.component.css']
})
export class MetricsComponent {
  currentImage = input<ImageRecord | null>(null);
}
