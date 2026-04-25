"use client";

import { CopilotKit } from "@copilotkit/react-core";
import Chat from "@/components/chat";
import MedDocPanel from "@/components/med-doc-panel";

export default function Home() {
  return (
    <div className="relative flex h-screen overflow-hidden bg-[#DEDEE9] p-2 gap-2">
      {/* Background blur circles */}
      <div
        className="absolute w-[445px] h-[445px] left-[1040px] top-[11px] rounded-full z-0"
        style={{ background: "rgba(255, 172, 77, 0.2)", filter: "blur(103px)" }}
      />
      <div
        className="absolute w-[609px] h-[609px] left-[1339px] top-[625px] rounded-full z-0"
        style={{ background: "#C9C9DA", filter: "blur(103px)" }}
      />
      <div
        className="absolute w-[609px] h-[609px] left-[670px] top-[-365px] rounded-full z-0"
        style={{ background: "#C9C9DA", filter: "blur(103px)" }}
      />
      <div
        className="absolute w-[445px] h-[445px] left-[128px] top-[331px] rounded-full z-0"
        style={{ background: "rgba(255, 243, 136, 0.3)", filter: "blur(103px)" }}
      />

      <CopilotKit runtimeUrl="/api/copilotkit" agent="medok_chat">
        <div className="flex flex-1 overflow-hidden z-10 gap-2">

          {/* Chat panel */}
          <div className="w-1/2 border-2 border-white bg-white/50 backdrop-blur-md shadow-elevation-lg flex flex-col rounded-lg overflow-hidden">
            <div className="p-6 border-b border-[#DBDBE5]">
              <h1 className="text-2xl font-semibold text-[#010507] mb-1">
                medokchat
              </h1>
              <p className="text-sm text-[#57575B] leading-relaxed">
                Assistant médical — informations sur les médicaments
              </p>
            </div>
            <div className="flex-1 overflow-hidden">
              <Chat />
            </div>
          </div>

          {/* Documentation panel */}
          <div className="w-1/2 border-2 border-white bg-white/50 backdrop-blur-md shadow-elevation-lg flex flex-col rounded-lg overflow-hidden">
            <div className="p-6 border-b border-[#DBDBE5]">
              <h2 className="text-2xl font-semibold text-[#010507] mb-1">
                Documentation officielle
              </h2>
              <p className="text-sm text-[#57575B] leading-relaxed">
                Base de données publique des médicaments (ANSM)
              </p>
            </div>
            <div className="flex-1 overflow-hidden">
              <MedDocPanel />
            </div>
          </div>

        </div>
      </CopilotKit>
    </div>
  );
}
