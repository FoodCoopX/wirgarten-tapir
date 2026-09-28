import React from "react";
import { PublicPickupLocation } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

interface PickupLocationFutureHintProps {
  pickupLocation: PublicPickupLocation;
  fontSize?: string;
  variant?: "warning" | "danger";
  children?: React.ReactNode;
}

const PickupLocationFutureHint: React.FC<PickupLocationFutureHintProps> = ({
  pickupLocation,
  fontSize = "1rem",
  variant = "warning",
  children,
}) => {
  const variantClass = variant === "danger" ? "text-danger" : "text-warning";
  return (
    <span className={`${variantClass} fst-italic`}>
      <span className="material-icons" style={{ fontSize }}>
        schedule
      </span>{" "}
      {children ??
        `Verfügbar ab: ${formatDateNumeric(new Date(pickupLocation.startDate!))}`}
    </span>
  );
};

export default PickupLocationFutureHint;