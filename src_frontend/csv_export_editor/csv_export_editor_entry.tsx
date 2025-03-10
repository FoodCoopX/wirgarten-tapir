import { createRoot } from "react-dom/client";
import CsvExportEditor from "./CsvExportEditor.tsx";

const domNode = document.getElementById("csv_export_editor");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<CsvExportEditor />);
} else {
  console.error("Failed to render csv editor from React");
}
