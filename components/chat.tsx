"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Chat() {
  return (
    <CopilotChat
      labels={{
        title: "Assistant Médical",
        initial:
          "Bonjour ! Je suis votre assistant médical. Posez-moi vos questions sur les médicaments : posologie, contre-indications, effets indésirables, notice...\n\nExemples :\n- \"Qu'est-ce que le Doliprane ?\"\n- \"Quelles sont les contre-indications de l'ibuprofène ?\"\n- \"Posologie de l'amoxicilline pour un adulte\"",
      }}
      className="h-full"
    />
  );
}
