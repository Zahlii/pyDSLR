import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CONFIG } from './config';

/**
 * Interface representing a print request
 */
export interface PrintRequest {
  image_path: string;
  copies?: number;
  landscape?: boolean;
  printer_name?: string | null;
}

export interface ExifInfo {
  iso: number | null;
  fstop: number | null;
  exposure_time: number | null;
  width: number;
  height: number;
}

export interface SnapshotResponse {
  image_path: string;
  image_b64: string;
  exif: ExifInfo | null;
}

@Injectable({
  providedIn: 'root',
})
export class CaptureService {
  constructor(private http: HttpClient) {}

  /**
   * Captures a snapshot from the camera
   * @returns An Observable with the snapshot data including image path, base64 image, and EXIF data
   */
  captureSnapshot(): Observable<SnapshotResponse> {
    return this.http.get<SnapshotResponse>(`${CONFIG.BACKEND_URL}/snapshot`);
  }

  /**
   * Deletes a previously captured snapshot
   * @param snapshotName The name of the snapshot to delete
   * @returns An Observable that resolves to true if deletion was successful
   */
  deleteSnapshot(snapshotName: string): Observable<boolean> {
    return this.http.delete<boolean>(`${CONFIG.BACKEND_URL}/snapshot`, {
      params: { snapshot_name: snapshotName },
    });
  }

  /**
   * Prints a captured snapshot with the specified options
   * @param printRequest The print request details including image path, copies, landscape orientation, and printer name
   * @returns An Observable that resolves to true if printing was successful
   */
  printSnapshot(printRequest: PrintRequest): Observable<boolean> {
    return this.http.post<boolean>(`${CONFIG.BACKEND_URL}/print`, printRequest);
  }
}
