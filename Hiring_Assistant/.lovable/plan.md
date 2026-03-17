
# CV Chatbot - Frontend Interface

## Overview
A sleek, dark-themed chatbot interface for CV/resume analysis. Users can upload CV images, select their preferred LLM provider (OpenAI, Gemini, or Anthropic), and chat with the AI about the uploaded CV. The backend URL points to `localhost` and API keys are stored in session only.

## Pages & Layout

### Main Chat Page
- **Dark glassmorphism theme** inspired by modern AI chat apps (ChatGPT/Claude style)
- Full-height layout with a sidebar and main chat area

### Sidebar
- **LLM Provider Selector** — toggle between OpenAI, Gemini, and Anthropic with branded icons
- **API Key Management** — button for each provider that opens a modal/dialog to enter and save the API key (session storage only, cleared on refresh)
- **Status indicators** showing which provider is active and whether its key is configured
- **New Chat** button to reset the conversation

### Chat Area
- Message bubbles with distinct styling for user vs assistant messages
- **Markdown rendering** for AI responses
- Auto-scroll to latest message
- Loading/typing indicator while waiting for response

### Input Bar (Bottom)
- Text input field with send button
- **Image upload button** — allows uploading CV images (drag & drop + click to browse)
- Image preview thumbnail before sending
- Support for common image formats (PNG, JPG, PDF preview)

### API Key Modal
- Clean dialog popup per provider (OpenAI / Gemini / Anthropic)
- Masked input field for the API key
- "Save" and "Cancel" buttons
- Visual confirmation when key is saved to session

## Technical Approach
- Frontend only — all API calls will be made to `http://localhost:PORT/chat` (configurable)
- API keys and selected model sent as headers/body to the backend
- Image converted to base64 before sending to backend
- Streaming support ready (SSE-compatible) for real-time responses
- Responsive design for desktop and mobile

## File Structure
- `src/pages/Chat.tsx` — main chat page
- `src/components/chat/` — ChatSidebar, ChatMessages, ChatInput, MessageBubble, ImageUploader
- `src/components/settings/` — ApiKeyModal, ProviderSelector
- `src/hooks/useChat.ts` — chat logic and API communication
- `src/lib/chatApi.ts` — API call utilities
- `src/types/chat.ts` — TypeScript types
