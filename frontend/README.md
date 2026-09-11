# tru-prompt-frontend

React app for storing, searching, filtering, and generating AI prompts. Users sign in via Microsoft SSO, describe an idea plus pick one or more "expert" categories (SEO, Design, Web Development, etc.), and the app returns a polished, reusable prompt plus a short "optimizer" (key context points). Results can be saved, browsed ("most used" community-wide, or "my saved"), copied, regenerated, and edited.

This frontend talks to [tru-prompt-backend](../tru-prompt-backend) (FastAPI + Supabase) for auth, storage, and AI generation — see that repo's README for backend setup, and the root [../README.md](../README.md) / [../TECHNICAL.md](../TECHNICAL.md) for how the two fit together.

## Setup

1. `npm install`
2. Create `.env` in this directory:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```
   (match whatever port the backend is actually running on)
3. `npm start` — runs the dev server at http://localhost:3000

## Available scripts

- `npm start` — dev server with hot reload
- `npm run build` — production build to `build/`
- `npm test` — CRA's interactive test runner

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app); see the [CRA docs](https://facebook.github.io/create-react-app/docs/getting-started) for details on the build tooling itself.

## Notes

- Login only works end-to-end once the backend has real Microsoft Entra (Azure AD) credentials configured. For local development without that, log in via the backend's `GET /api/users/auth/dev-login` instead of the "Login with Microsoft" button.
- Prompt generation (`openAIUtils.js`) calls the backend's `/api/ai/generate-prompt` — the OpenAI key lives server-side only, never in this app.
