import { createRoot } from "react-dom/client";
import GrowingPeriodBase from "./GrowingPeriodBase.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import ProductBase from "./ProductBase.tsx";

const domNodeGrowingPeriodButton = document.getElementById(
  "edit_growing_period_button",
);
if (domNodeGrowingPeriodButton) {
  const root = createRoot(domNodeGrowingPeriodButton);

  root.render(<GrowingPeriodBase csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render growing period button from React");
}

const domNodeProductButton = document.getElementById("edit_product_button");
if (domNodeProductButton) {
  const root = createRoot(domNodeProductButton);

  root.render(<ProductBase csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render product button from React");
}
