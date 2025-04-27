import { Component } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-welcome-screen',
  imports: [MatButton, RouterLink],
  templateUrl: './welcome-screen.component.html',
  styleUrl: './welcome-screen.component.less',
})
export class WelcomeScreenComponent {}
