import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import AdminDashboardAssociationDataBase from "./AdminDashboardAssociationDataBase.tsx";
import DashboardPickupLocationCapacityBase from "./DashboardPickupLocationCapacityBase.tsx";

const domNodePickupLocations = document.getElementById(
  "dashboard_pickup_location_entry",
);
if (domNodePickupLocations) {
  const root = createRoot(domNodePickupLocations);

  root.render(<DashboardPickupLocationCapacityBase />);
} else {
  console.error("Failed to render pickup location capacities from React");
}

const domNodeAssociations = document.getElementById(
  "association_memberships_dashboard",
);
if (domNodeAssociations) {
  const root = createRoot(domNodeAssociations);
  root.render(<AdminDashboardAssociationDataBase csrfToken={getCsrfToken()} />);
}
