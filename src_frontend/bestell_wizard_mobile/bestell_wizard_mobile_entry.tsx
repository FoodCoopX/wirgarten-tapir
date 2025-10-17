import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BestellWizardMobile from "./BestellWizardMobile.tsx";

const domNode = document.getElementById("bestell_wizard_mobile");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<BestellWizardMobile csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render bestell wizard mobile from React");
}
