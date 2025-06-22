import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CONFIG } from './config';

/**
 * Interface representing a layout configuration
 */
export interface Layout {
  file: string | null;
  layout: string;
  name: string;
  n_images: number;
}

/**
 * Interface representing a print request
 */
export interface PrintRequest {
  image_path: string;
  copies?: number;
  landscape?: boolean;
  printer_name?: string | null;
  cmd_args?: string[];
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
  image_path_camera_raw?: string;
  image_b64: string;
  exif: ExifInfo | null;
  all_paths: string[];
}

export interface BoothConfig {
  countdown_capture_seconds: number;
  inactivity_return_seconds: number;
  booth_title: string;
  default_printer: string;
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

  getConfig(): Observable<BoothConfig> {
    /**
     * Get the active config.
     */
    return this.http.get<BoothConfig>(`${CONFIG.BACKEND_URL}/config`);
  }

  /**
   * Deletes previously captured snapshots
   * @param snapshotNames The names of the snapshots to delete
   * @returns An Observable that resolves to true if deletion was successful
   */
  deleteSnapshots(snapshotNames: string[]): Observable<boolean> {
    return this.http.delete<boolean>(`${CONFIG.BACKEND_URL}/snapshots`, {
      body: snapshotNames,
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

  /**
   * Retrieves available layouts from the backend
   * @returns An Observable with array of available layouts
   */
  getAvailableLayouts(): Observable<Layout[]> {
    return this.http.get<Layout[]>(`${CONFIG.BACKEND_URL}/available_layouts`);
  }

  /**
   * Sets the current layout configuration
   * @param layout The layout configuration to set
   * @returns An Observable that resolves to true if the layout was set successfully
   */
  setLayout(layout: Layout): Observable<boolean> {
    return this.http.post<boolean>(`${CONFIG.BACKEND_URL}/layout`, layout);
  }

  /**
   * Renders a layout with the given image names
   * @param imageNames Array of image names to render in the layout
   * @returns An Observable with the rendered snapshot response
   */
  renderLayout(imageNames: string[]): Observable<SnapshotResponse> {
    return this.http.post<SnapshotResponse>(
      `${CONFIG.BACKEND_URL}/layout/render`,
      imageNames,
    );
  }
}
