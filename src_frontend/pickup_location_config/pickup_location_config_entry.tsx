import { createRoot } from "react-dom/client";
import LocationRouteBase from "./LocationRouteBase.tsx";
import PickupLocationCapacityBase from "./PickupLocationCapacityBase.tsx";
import PickupLocationEditBase from "./PickupLocationEditBase.tsx";

const domNodeEditButtons = document.getElementById(
  "pickup_location_edit_buttons",
);
if (domNodeEditButtons) {
  createRoot(domNodeEditButtons).render(<PickupLocationEditBase />);
} else {
  console.error("Failed to render pickup location edit buttons from React");
}

const domNodeCapacityButton = document.getElementById(
  "pickup_location_capacity_edit_button",
);
if (domNodeCapacityButton) {
  const enableDeliveryCharge =
    domNodeCapacityButton.dataset.enableDeliveryCharge === "True";
  const root = createRoot(domNodeCapacityButton);

  root.render(
    <PickupLocationCapacityBase enableDeliveryCharge={enableDeliveryCharge} />,
  );
} else {
  console.error("Failed to render pickup location capacity button from React");
}

const domNodeLocationRoute = document.getElementById("manage_location_rouge");
if (domNodeLocationRoute) {
  const root = createRoot(domNodeLocationRoute);

  root.render(<LocationRouteBase />);
} else {
  console.error("Failed to render pickup location capacity button from React");
}
