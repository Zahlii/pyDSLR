const BACKEND_URL = 'http://localhost:8000/api';

export const CONFIG = {
  COUNTDOWN_CAPTURE_SECONDS: 10,
  INACTIVITY_RETURN_SECONDS: 30,
  BACKEND_URL,
  BACKEND_STREAM_URL: BACKEND_URL + '/stream',
  BACKEND_LAST_URL: BACKEND_URL + '/last',
};
