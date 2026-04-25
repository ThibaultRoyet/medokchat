"use client";

import { useCoAgent } from "@copilotkit/react-core";

interface AgentState {
  current_med_documentation?: string;
}

export default function MedDocPanel() {
  const { state } = useCoAgent<AgentState>({ name: "medok_chat" });
  const html = state?.current_med_documentation;

  if (!html) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#57575B] gap-3">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-30">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        <p className="text-sm opacity-50">Ask about a medication to see its official documentation</p>
      </div>
    );
  }

  // Inject a <base> tag so relative assets (CSS, images) resolve correctly
  const htmlWithBase = html.replace(
    /<head([^>]*)>/i,
    `<head$1><base href="https://base-donnees-publique.medicaments.gouv.fr/">`
  );

  return (
    <iframe
      srcDoc={htmlWithBase}
      className="w-full h-full border-0"
      sandbox="allow-same-origin allow-scripts"
      title="Medication documentation"
    />
  );
}
