# ImageCyte Frontend Client

This directory contains the Angular single-page application dashboard.

---

## 1. Technology Stack
- **Framework**: Angular standalone components (17+)
- **Styling**: Vanilla CSS (sleek dark glassmorphic UI)
- **Data Flow & Observables**: RxJS (BehaviorSubjects, pipes)
- **Visuals**: HTML5 Canvas (custom metrics histogram drawing)

---

## 2. Directory & Code Structure
```
frontend/
└── src/
    ├── app/
    │   ├── core/
    │   │   ├── guards/
    │   │   │   └── auth.guard.ts         → Routes access control guard
    │   │   ├── interceptors/
    │   │   │   └── auth.interceptor.ts   → Bearer token injection & 401 token refresh queue
    │   │   ├── models/
    │   │   │   └── image.model.ts        → Client-side TypeScript interfaces
    │   │   └── services/
    │   │       ├── auth.service.ts       → Login, refresh token, and localStorage operations
    │   │       └── image.service.ts      → Image endpoint requests
    │   ├── features/
    │   │   ├── login/                    → Login form page standalone component
    │   │   └── dashboard/                → Dashboard standalone component orchestrator
    │   │       ├── components/
    │   │       │   ├── histogram/        → Intensity distribution canvas chart
    │   │       │   ├── metrics/          → Metric cards and classification stats
    │   │       │   ├── timeline-scrub-bar/ → Chronological history timeline player
    │   │       │   └── viewport/         → Raw microscopy viewer & stackable overlays
    │   │       └── dashboard.component.ts
    │   ├── app.component.ts              → Main root client layout
    │   └── app.config.ts                 → Client provider definitions & interceptor registrations
    └── styles.css                        → Global application theme & CSS variables
```

---

## 3. Main Functional Modules & Code Parts

### A. Viewport & Stackable Transparent Overlays
- **Location**: `features/dashboard/components/viewport/`
- **Logic**: Renders the raw base64 image BGR buffer.
- **Overlay Stacking**: Displays Canny and Otsu overlays using absolute CSS positioning stacked directly on top of the raw viewport container. Users can toggle layers individually or view them simultaneously.

### B. Chronological Video-Player Timeline Scrub Bar
- **Location**: `features/dashboard/components/timeline-scrub-bar/`
- **Hover Coordinate Calculations**: Maps cursor horizontal coordinates relative to the player width to retrieve historical frames chronologically.
- **Preview Tooltip**: Displays a floating popup containing the `120x90` frame preview thumbnail, timestamp, and metrics. Clicking a timeline location locks that snapshot and updates the main feed.

### C. Live Custom Intensity Canvas Histogram
- **Location**: `features/dashboard/components/histogram/`
- **HTML5 Canvas Drawing**: Receives a 256-index frequency distribution array and plots it dynamically on an HTML5 canvas. Columns are colored using neon gradient fills that match the GFP microscopy aesthetic.

---

## 4. Concurrency-Safe HTTP Interceptor (`auth.interceptor.ts`)
The `authInterceptor` handles expired access token failures (401 Unauthorized) transparently while safeguarding against desynchronized session disconnects:
- **Redundant Refresh Prevention**: If multiple concurrent API requests fail with 401, only the first request initiates the POST call to `/api/proxy/refresh`.
- **Token Reuse Check**: Parallel requests wait on a `BehaviorSubject` and read the updated token once the refresh finishes. Before making a new refresh request, it checks if `currentToken !== requestToken`. If another thread has already refreshed the token in the background, it retries immediately with the new token.
- **Auth Endpoint Bypass**: Bypasses the interceptor loop for `/api/proxy/login` and `/api/proxy/refresh` endpoints.

---

## 5. Verification & Testing

### Running Client Unit Tests
Execute unit tests for guards, standalone components, interceptors, and canvas chart logic inside the frontend container:
```bash
docker-compose exec frontend npx ng test --no-watch
```
---
