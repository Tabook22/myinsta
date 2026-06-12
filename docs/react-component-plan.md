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

- Text input for an Instagram or YouTube URL.
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
- Lets the user switch between original, cleaned, and Arabic cleaned text.
- Later: add timestamped segment list.

### `ChatPanel`

- Shows chat history.
- Lets the user choose transcript or web answer mode.
- Lets the user choose English, Arabic, or bilingual answers.
- Sends message, mode, and answer language to `POST /api/videos/{video_id}/chat`.

## API client

`src/api/client.js` exports:

- `createVideo(url)`
- `getVideo(videoId)`
- `listVideos()`
- `cleanTranscript(videoId, targetLanguage)`
- `chatWithVideo(videoId, message, mode, answerLanguage)`

## State management

Use React `useState` and `useEffect` only for v1. Do not add app-wide state libraries until needed.
