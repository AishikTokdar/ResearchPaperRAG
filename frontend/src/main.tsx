/**
 * Application Entry Point
 *
 * Initializes Sentry (before anything else), then mounts the React app.
 *
 * StrictMode double-invokes certain effects in dev only — helps catch unsafe side effects.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { initSentry } from "@/lib/sentry";
import App from "./App";
import "./styles/globals.css";

initSentry();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
