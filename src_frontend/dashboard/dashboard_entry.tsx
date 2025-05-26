import { createRoot } from "react-dom/client";
import DashboardPickupLocationCapacityBase from "./DashboardPickupLocationCapacityBase.tsx";

const domNode = document.getElementById("dashboard_pickup_location_entry");
if (domNode) {
  const root = createRoot(domNode);

  root.render(<DashboardPickupLocationCapacityBase />);
} else {
  console.error("Failed to render pickup location capacities from React");
}
