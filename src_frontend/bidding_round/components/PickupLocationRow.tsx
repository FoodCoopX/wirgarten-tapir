import React from "react";

import { CurrentPickupLocation, RoundTexts } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import {
  DELIVERY_CHARGE_LABEL,
  getPickupLocationTitle,
} from "../utils/pickupLocation.ts";
import PickupLocationHint from "./PickupLocationHint.tsx";

interface PickupLocationRowProps {
  currentPickupLocation: CurrentPickupLocation | null;
  texts: RoundTexts;
  variant: "stacked" | "inline";
  showDeliveryCharge?: boolean;
}

const PickupLocationRow: React.FC<PickupLocationRowProps> = ({
  currentPickupLocation,
  texts,
  variant,
  showDeliveryCharge = true,
}) => {
  if (!currentPickupLocation) {
    return null;
  }

  const title = getPickupLocationTitle(texts);
  const yearlyDeliveryCharge = Number(
    currentPickupLocation.yearlyDeliveryCharge,
  );
  const monthlyDeliveryCharge = yearlyDeliveryCharge / 12;

  if (variant === "inline") {
    return (
      <div className={"d-flex justify-content-between"}>
        <span className={"text-muted"}>{title}</span>
        <span className={"d-inline-flex align-items-center"}>
          <strong>
            {currentPickupLocation.name}
            {showDeliveryCharge &&
              monthlyDeliveryCharge > 0 &&
              ` (+ ${formatCurrency(monthlyDeliveryCharge)} ${DELIVERY_CHARGE_LABEL})`}
          </strong>
          <PickupLocationHint />
        </span>
      </div>
    );
  }

  return (
    <div className={"d-flex flex-column gap-1"}>
      <div className={"d-flex justify-content-between align-items-center"}>
        <span className={"text-muted"}>{title}</span>
        <span>
          <strong>{currentPickupLocation.name}</strong>
          <PickupLocationHint />
        </span>
      </div>
      {showDeliveryCharge && monthlyDeliveryCharge > 0 && (
        <div className={"d-flex justify-content-between"}>
          <span className={"text-muted"}>{DELIVERY_CHARGE_LABEL}</span>
          <strong>{formatCurrency(monthlyDeliveryCharge)}</strong>
        </div>
      )}
    </div>
  );
};

export default PickupLocationRow;
