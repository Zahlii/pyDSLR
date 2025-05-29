import {
  Component,
  OnDestroy,
  OnInit,
  signal,
  WritableSignal,
} from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { firstValueFrom, interval, Subscription } from 'rxjs';
import { CaptureService, Layout, SnapshotResponse } from '../capture.service';
import { CONFIG } from '../config';
import { PrintDialogComponent } from '../print-dialog/print-dialog.component';

@Component({
  selector: 'app-capture-screen',
  imports: [MatButton],
  templateUrl: './capture-screen.component.html',
  styleUrl: './capture-screen.component.scss',
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
  protected layout: Layout = {
    layout: '1',
    file: null,
    n_images: 1,
    name: 'Default',
  };
  private snapshotStack: SnapshotResponse[] = [];

  constructor(
    private cs: CaptureService,
    private router: Router,
    private dialog: MatDialog,
  ) {}

  ngOnInit() {
    this.startInactivityTimer();
    this.reset().then();
    this.layout = history.state as Layout;
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

  private async restartStream() {
    this.activeStream.set(CONFIG.BACKEND_STREAM_URL);
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }

  private async reset() {
    this.snapshotStack = [];
    this.activeSnapshot.set(undefined);
    this.countDownActive.set(false);
    this.captureActive.set(false);

    await this.restartStream();
  }

  protected async leave() {
    await this.cancelStream();
    this.snapshotStack = [];
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

  async countDownAndSnapshot(count: number = 1, delaySeconds?: number) {
    await this.restartStream();

    this.resetInactivityTimer();
    this.countDownActive.set(true);
    this.countDownRemaining.set(
      delaySeconds || CONFIG.COUNTDOWN_CAPTURE_SECONDS,
    );

    await new Promise<void>((resolve) => {
      const int = setInterval(() => {
        this.countDownRemaining.update((v) => v - 1);
        if (this.countDownRemaining() <= 0) {
          clearInterval(int);
          resolve();
        }
      }, 1000);
    });

    this.countDownActive.set(false);
    await this.takeSnapshot(count);
  }

  async takeSnapshot(count: number = 1) {
    this.resetInactivityTimer();
    await this.cancelStream();

    this.captureActive.set(true);
    const res = await firstValueFrom(this.cs.captureSnapshot());
    this.snapshotStack.push(res);
    this.captureActive.set(false);

    if (count === 1) {
      // finished with all
      await this.cancelStream();
      const finalRes = await firstValueFrom(
        this.cs.renderLayout(this.snapshotStack.map((s) => s.image_path)),
      );
      this.activeSnapshot.set(finalRes);
      this.snapshotStack.push(finalRes); // for deletion
    } else {
      await this.countDownAndSnapshot(
        count - 1,
        CONFIG.COUNTDOWN_CAPTURE_SECONDS,
      );
    }
  }

  async delete() {
    await firstValueFrom(
      this.cs.deleteSnapshots(this.snapshotStack.flatMap((s) => s.all_paths)),
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
    await this.countDownAndSnapshot(this.layout.n_images);
  }

  async save(print = true) {
    this.resetInactivityTimer();
    if (print) {
      const dialogRef = this.dialog.open(PrintDialogComponent, {
        width: '300px',
        disableClose: true,
      });

      const result = await firstValueFrom(dialogRef.afterClosed());

      if (result) {
        await firstValueFrom(
          this.cs.printSnapshot({
            image_path: this.activeSnapshot()!.image_path,
            copies: result.copies,
            landscape: true,
            printer_name: 'Canon_SELPHY_CP1500',
            cmd_args: ['-o', 'PageSize=Postcard.Fullbleed'],
          }),
        );
      } else {
        return; // User cancelled the print operation
      }
    }
    await this.leave();
  }

  protected readonly CONFIG = CONFIG;
}
