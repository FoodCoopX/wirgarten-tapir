import { createRoot } from "react-dom/client";
import PdfExportEditor from "./PdfExportEditor.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("pdf_export_editor");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<PdfExportEditor csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render pdf editor from React");
}
