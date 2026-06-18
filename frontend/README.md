# CLEAR Frontend

This is the frontend application for CLEAR (Clearance & Logistics Engine for Authority Response), built with React, TypeScript, Vite, Tailwind CSS, TanStack Query, and MapLibre GL.

## Requirements

- Node.js (v18+)
- The CLEAR Backend running (or accessible via URL)

## Environment Variables

To connect to the backend, you must configure the following environment variables. Create a `.env.local` file in this directory with the following keys:

```env
# The base URL of the CLEAR backend
VITE_CLEAR_API_BASE=http://localhost:8000

# Operator token (required for Operator Console access)
VITE_CLEAR_OPERATOR_TOKEN=your_operator_token

# Citizen token (required for Citizen Portal access)
VITE_CLEAR_CITIZEN_TOKEN=your_citizen_token
```

> **Warning**: Never commit real production tokens to version control. The tokens dictate the scope and features visible in the application.

## CORS Configuration

The backend is already configured to allow CORS for `http://localhost:5173`. 
**If you deploy this frontend to a different URL**, the operator MUST add your deployed origin to the backend's `CLEAR_CORS_ALLOW_ORIGINS` environment variable for the API to function. No code changes are required in the frontend.

## Running Locally

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```

3. Open your browser to `http://localhost:5173`. Depending on the tokens provided in your `.env.local`, you will be routed to either the Operator Console or the Citizen Portal.
