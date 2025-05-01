import { Component, Input } from '@angular/core';
import { Layout } from '../../capture.service';
import { CONFIG } from '../../config';

@Component({
  selector: 'app-layout-preview',
  imports: [],
  templateUrl: './layout-preview.component.html',
  styleUrl: './layout-preview.component.less',
})
export class LayoutPreviewComponent {
  @Input() layout!: Layout;
  protected readonly CONFIG = CONFIG;
}
