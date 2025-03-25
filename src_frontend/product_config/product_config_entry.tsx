import { createRoot } from "react-dom/client";
import GrowingPeriodBase from "./GrowingPeriodBase.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";

const domNode = document.getElementById("edit_growing_period_button");
if (domNode) {
  const root = createRoot(domNode);

  root.render(<GrowingPeriodBase csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render growing period button from React");
}
