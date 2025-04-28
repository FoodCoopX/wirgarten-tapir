import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import PickupLocationCapacityBase from "./PickupLocationCapacityBase.tsx";

const domNode = document.getElementById("pickup_location_capacity_edit_button");
if (domNode) {
  const root = createRoot(domNode);

  root.render(<PickupLocationCapacityBase csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render pickup location capacity button from React");
}
