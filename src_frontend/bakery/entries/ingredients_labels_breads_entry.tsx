import { createRoot } from "react-dom/client";
import { IngredientsLabelsBreads } from "../pages";

const container = document.getElementById("ingredients-labels-breads-root");

if (container) {
  const csrfToken = container.dataset.csrfToken ?? "";
  const root = createRoot(container);
  root.render(<IngredientsLabelsBreads csrfToken={csrfToken} />);
}
