import {
  Component,
  OnDestroy,
  OnInit,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatButton } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom, interval, Subscription, timer } from 'rxjs';
import { CaptureService, SnapshotResponse } from '../capture.service';
import { CONFIG } from '../config';

@Component({
  selector: 'app-capture-screen',
  imports: [MatButton],
  templateUrl: './capture-screen.component.html',
  styleUrl: './capture-screen.component.less',
})
export class CaptureScreenComponent implements OnInit, OnDestroy {
  countDownActive = signal(false);
  captureActive = signal(false);
  countDownRemaining = signal(CONFIG.COUNTDOWN_CAPTURE_SECONDS);

  activeSnapshot: WritableSignal<SnapshotResponse | undefined> =
    signal(undefined);
  activeStream: WritableSignal<string | undefined> = signal(
    CONFIG.BACKEND_STREAM_URL,
  );

  private inactivityTimer: Subscription | null = null;

  constructor(
    private cs: CaptureService,
    private router: Router,
  ) {}

  ngOnInit() {
    this.startInactivityTimer();
    this.reset();
  }

  ngOnDestroy() {
    this.clearInactivityTimer();
  }

  private startInactivityTimer() {
    this.clearInactivityTimer();
    this.inactivityTimer = interval(1000).subscribe(async (i) => {
      if (i >= CONFIG.INACTIVITY_RETURN_SECONDS && !this.activeSnapshot()) {
        this.clearInactivityTimer();
        await this.leave();
      }
    });
  }

  private async cancelStream() {
    this.activeStream.set(undefined);
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }

  private async reset() {
    this.activeSnapshot.set(undefined);
    this.countDownActive.set(false);
    this.captureActive.set(false);

    this.activeStream.set(CONFIG.BACKEND_STREAM_URL);
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }

  private async leave() {
    await this.cancelStream();
    this.activeSnapshot.set(undefined);
    this.countDownActive.set(false);
    this.captureActive.set(false);
    // wait until changes are propagated, i.e. image source is really set
    await this.router.navigate(['']);
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
    this.countDownRemaining.set(CONFIG.COUNTDOWN_CAPTURE_SECONDS);

    const subCountDown = interval(1000).subscribe(async (_) => {
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
    await this.cancelStream();

    this.captureActive.set(true);
    const res = await firstValueFrom(this.cs.captureSnapshot());
    this.activeSnapshot.set(res);
    this.captureActive.set(false);
  }

  async delete() {
    await firstValueFrom(
      this.cs.deleteSnapshot(this.activeSnapshot()!.image_path),
    );
  }

  async deleteAndLeave() {
    await this.delete();
    await this.leave();
  }

  async deleteAndRetry() {
    this.resetInactivityTimer();
    await this.delete();
    await this.reset();
    this.startCountDown();
  }

  async saveAndPrint() {
    this.resetInactivityTimer();
    await firstValueFrom(
      this.cs.printSnapshot({
        image_path: this.activeSnapshot()!.image_path,
        copies: 1,
        landscape: true,
      }),
    );
    await this.leave();
  }

  protected readonly CONFIG = CONFIG;
}
