import { Component, Input } from '@angular/core';
import { Layout } from '../../capture.service';
import { CONFIG } from '../../config';
import {
  MatCard,
  MatCardContent,
  MatCardHeader,
  MatCardSubtitle,
  MatCardTitle,
} from '@angular/material/card';
import { MatGridTile } from '@angular/material/grid-list';

@Component({
  selector: 'app-layout-preview',
  imports: [
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardSubtitle,
    MatCardContent,
  ],
  templateUrl: './layout-preview.component.html',
  styleUrl: './layout-preview.component.scss',
})
export class LayoutPreviewComponent {
  @Input() layout!: Layout;
  protected readonly CONFIG = CONFIG;
}
