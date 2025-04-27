import { Routes } from '@angular/router';
import { WelcomeScreenComponent } from './welcome-screen/welcome-screen.component';
import { CaptureScreenComponent } from './capture-screen/capture-screen.component';

export const routes: Routes = [
  { path: '', component: WelcomeScreenComponent },
  { path: 'preview', component: CaptureScreenComponent },
];
