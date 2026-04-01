import { createRoot } from "react-dom/client";
import CsvExportEditor from "./CsvExportEditor.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("csv_export_editor");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<CsvExportEditor csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render csv editor from React");
}
