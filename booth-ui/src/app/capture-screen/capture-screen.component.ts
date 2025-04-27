import {
  Component,
  OnDestroy,
  OnInit,
  signal,
  WritableSignal,
} from '@angular/core';
import { MatButton } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';
import { interval, Subscription } from 'rxjs';
import { CaptureService, SnapshotResponse } from '../capture.service';

const COUNTDOWN = 3;
const RETURN_AFTER = 10;
const STREAM = 'http://localhost:8000/api/stream';

@Component({
  selector: 'app-capture-screen',
  imports: [MatButton],
  templateUrl: './capture-screen.component.html',
  styleUrl: './capture-screen.component.less',
})
export class CaptureScreenComponent implements OnInit, OnDestroy {
  countDownActive = signal(false);
  countDownRemaining = signal(COUNTDOWN);
  activeStream: WritableSignal<string | undefined> = signal(STREAM);

  activeSnapshot: WritableSignal<SnapshotResponse | undefined> =
    signal(undefined);

  private inactivityTimer: Subscription | null = null;

  constructor(
    private cs: CaptureService,
    private router: Router,
  ) {}

  ngOnInit() {
    this.startInactivityTimer();
  }

  ngOnDestroy() {
    this.clearInactivityTimer();
  }

  private startInactivityTimer() {
    this.clearInactivityTimer();
    this.inactivityTimer = interval(1000).subscribe(async (i) => {
      if (i >= RETURN_AFTER) {
        this.clearInactivityTimer();
        this.activeStream.set(undefined);
        this.activeSnapshot.set(undefined);
        this.countDownActive.set(false);
        await this.router.navigate(['']);
      }
    });
  }

  private clearInactivityTimer() {
    if (this.inactivityTimer) {
      this.inactivityTimer.unsubscribe();
      this.inactivityTimer = null;
    }
  }

  private resetInactivityTimer() {
    this.startInactivityTimer();
  }

  startCountDown() {
    this.resetInactivityTimer();
    this.countDownActive.set(true);
    this.countDownRemaining.set(COUNTDOWN);
    const subCountDown = interval(1000).subscribe(async (i) => {
      this.countDownRemaining.update((v) => v - 1);
      if (this.countDownRemaining() <= 0) {
        subCountDown.unsubscribe();
        this.countDownActive.set(false);
        await this.takeSnapshot();
      }
    });
  }

  async takeSnapshot() {
    this.resetInactivityTimer();
    this.activeStream.set(undefined);
    this.cs.captureSnapshot().subscribe((res) => {
      this.activeSnapshot.set(res);
    });
  }

  async deleteSnapshot() {
    this.resetInactivityTimer();
    this.activeStream.set(STREAM);
    this.cs.deleteSnapshot(this.activeSnapshot()!.image_path).subscribe((_) => {
      this.activeSnapshot.set(undefined);
      this.startCountDown();
    });
  }

  async saveAndPrintSnapshot() {
    this.resetInactivityTimer();
    this.cs
      .printSnapshot({
        image_path: this.activeSnapshot()!.image_path,
        copies: 1,
        landscape: true,
      })
      .subscribe((_) => {
        this.router.navigate(['']);
      });
  }
}
