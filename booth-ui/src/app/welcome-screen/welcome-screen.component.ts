import { Component, OnInit, signal, WritableSignal } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';
import { CaptureService, Layout } from '../capture.service';
import { firstValueFrom } from 'rxjs';
import { LayoutPreviewComponent } from './layout-preview/layout-preview.component';

@Component({
  selector: 'app-welcome-screen',
  imports: [LayoutPreviewComponent],
  templateUrl: './welcome-screen.component.html',
  styleUrl: './welcome-screen.component.less',
})
export class WelcomeScreenComponent implements OnInit {
  availableLayouts: WritableSignal<any> = signal([]);

  constructor(
    private cs: CaptureService,
    private router: Router,
  ) {}

  ngOnInit() {
    this.cs.getAvailableLayouts().subscribe(this.availableLayouts.set);
  }

  async choseLayout(layout: Layout) {
    await firstValueFrom(this.cs.setLayout(layout));
    await this.router.navigate(['preview'], { state: layout });
  }
}
