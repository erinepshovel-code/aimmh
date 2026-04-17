// "lines of code":"25","lines of commented":"0"
import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const VIEWPORT_CONTENT = "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no";

function enforceViewportMeta() {
  let viewport = document.querySelector('meta[name="viewport"]');
  if (!viewport) {
    viewport = document.createElement('meta');
    viewport.setAttribute('name', 'viewport');
    document.head.appendChild(viewport);
  }
  if (viewport.getAttribute('content') !== VIEWPORT_CONTENT) {
    viewport.setAttribute('content', VIEWPORT_CONTENT);
  }
}

enforceViewportMeta();
const viewportObserver = new MutationObserver(() => enforceViewportMeta());
viewportObserver.observe(document.head, { childList: true, subtree: true, attributes: true });

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
// "lines of code":"25","lines of commented":"0"
