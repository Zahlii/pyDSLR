import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatToolbar } from '@angular/material/toolbar';
import { CaptureService } from './capture.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatToolbar],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  protected title: string = 'Photo Booth';
  constructor(protected service: CaptureService) {
    this.service.getConfig().subscribe((config) => {
      this.title = config.booth_title;
    });
  }
}
