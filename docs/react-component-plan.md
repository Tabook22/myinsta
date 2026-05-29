# React Page and Component Plan

## Page

### `HomePage`

Responsibilities:

- Hold selected/current video state.
- Submit URLs through the API client.
- Poll the backend while video status is `queued` or `processing`.
- Render details, transcript, and chat panel.

## Components

### `UrlSubmitForm`

- Text input for Instagram URL.
- Submit button.
- Calls `onSubmit(url)`.
- Disables button while submitting.

### `VideoDetails`

- Shows title/status/source URL.
- Shows uploader and duration when available.
- Shows error message if status is `failed`.

### `TranscriptViewer`

- Shows full transcript text when available.
- Shows waiting/empty state while processing.
- Later: add timestamped segment list.

### `ChatPanel`

- Shows placeholder chat box.
- Sends message to `POST /api/videos/{video_id}/chat`.
- Later: render chat history and cited transcript snippets.

## API client

`src/api/client.js` exports:

- `createVideo(url)`
- `getVideo(videoId)`
- `listVideos()`
- `chatWithVideo(videoId, message)`

## State management

Use React `useState` and `useEffect` only for v1. Do not add app-wide state libraries until needed.
