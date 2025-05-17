import { Component } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-print-dialog',
  templateUrl: './print-dialog.component.html',
  styleUrls: ['./print-dialog.component.scss'],
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
})
export class PrintDialogComponent {
  printForm: FormGroup;

  copies: number[] = [1, 2, 3, 4];

  constructor(
    private dialogRef: MatDialogRef<PrintDialogComponent>,
    private fb: FormBuilder,
  ) {
    this.printForm = this.fb.group({
      copies: [1, Validators.required],
    });
  }

  onCancelClick(): void {
    this.dialogRef.close();
  }

  onPrintClick(): void {
    if (this.printForm.valid) {
      this.dialogRef.close(this.printForm.value);
    }
  }
}
