import { createRoot } from "react-dom/client";
import { Reports } from "../pages";

const container = document.getElementById("reports-root");

if (container) {
  const csrfToken = container.dataset.csrfToken ?? "";
  const root = createRoot(container);
  root.render(<Reports csrfToken={csrfToken} />);
}
