import { createRoot } from "react-dom/client";
import { WeeklyPlanBreads } from "../pages";

const container = document.getElementById("weekly-plan-breads-root");

if (container) {
  const root = createRoot(container);
  root.render(<WeeklyPlanBreads />);
}
