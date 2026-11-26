import { createRoot } from "react-dom/client";
import { WeeklyPlanBreads } from "../pages";

const container = document.getElementById("weekly-plan-breads-root");

if (container) {
  const csrfToken = container.dataset.csrfToken ?? "";
  const root = createRoot(container);
  root.render(<WeeklyPlanBreads csrfToken={csrfToken} />);
}
