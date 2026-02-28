import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BestellWizard from "./BestellWizard.tsx";

const domNode = document.getElementById("bestell_wizard");
if (domNode) {
  const pseudonymEnabled = domNode.dataset.pseudonymEnabled === "True";
  
  const root = createRoot(domNode);
  root.render(
    <BestellWizard 
      csrfToken={getCsrfToken()} 
      pseudonymEnabled={pseudonymEnabled}
    />
  );
} else {
  console.error("Failed to render bestell wizard from React");
}
