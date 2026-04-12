# User Analytics Section

This is a completely separate mini-project inside the current workspace. It does not modify any existing folders.

## What is included

- `frontend/`: browser-ready dashboard for job seekers
- `backend/`: no-dependency API layer that accepts CV text and generates analytics
- `shared/`: neutral empty-state payload shared by both frontend and backend

## Current behavior

- The dashboard starts in a neutral empty state instead of showing fake candidate values.
- When a user pastes CV text and clicks `Analyze CV`, the frontend sends the CV to the backend.
- The backend calls the configured OpenAI model from `.env` and returns the generated analytics payload.
- The separate `AI Assistant` button opens the Hiring Assistant URL in a new tab.

## Folder overview

- `frontend/index.html`: main analytics UI
- `frontend/script.js`: dashboard rendering plus CV submission flow
- `frontend/config.js`: frontend connection settings and default Hiring Assistant URL
- `backend/server.js`: simple no-dependency API server
- `backend/services/analyticsService.js`: OpenAI CV analysis plus in-memory session payload
- `shared/analytics-fallback-data.js`: common empty-state payload

## How to use

1. Fill `.env` with your OpenAI API key.
2. Start the backend with `node backend/server.js`.
3. Open `frontend/index.html` in a browser.
4. Paste CV text into the input area or load a PDF/text CV file, then click `Analyze CV`.
5. Click `AI Assistant` to open the Hiring Assistant URL.

## Environment variables

- `OPENAI_API_KEY`: required for CV analysis
- `OPENAI_MODEL`: defaults to `gpt-4o`
- `HIRING_ASSISTANT_URL`: defaults to `http://localhost:8080`
- `PORT`: backend port, defaults to `4500`
- `CORS_ORIGIN`: defaults to `*`
- `REQUEST_TIMEOUT_MS`: request timeout for OpenAI calls
- `EXPOSE_INTERNAL_ERRORS`: set to `true` only when debugging locally

## Notes

- No external packages are required for the backend code.
- The frontend can load text files and PDFs that contain selectable text.
- Scanned PDFs and DOCX files are still not parsed automatically, so paste extracted text for those cases.
