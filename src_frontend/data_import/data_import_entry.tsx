import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken";
import DataImportPage from "./DataImportPage";

const node = document.getElementById("data_import");
if (node)
  createRoot(node).render(<DataImportPage csrfToken={getCsrfToken()} />);
