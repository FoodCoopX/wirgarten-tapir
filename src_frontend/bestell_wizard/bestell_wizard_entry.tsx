import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import BestellWizard from "./BestellWizard.tsx";

const domNode = document.getElementById("bestell_wizard");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<BestellWizard csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render bestell wizard from React");
}
