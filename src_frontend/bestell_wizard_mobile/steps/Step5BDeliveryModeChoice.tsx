import React from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { DeliveryMode } from "../types/DeliveryMode.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { buildDeliveryChargeBadge } from "../utils/buildDeliveryChargeBadge.tsx";
import "../utils/flexColOnSmallScreen.css";
import { getPickupLocationsForDeliveryMode } from "../utils/getPickupLocationsForDeliveryMode.ts";

interface Step5BDeliveryModeChoiceProps {
  settings: BestellWizardSettings;
  onDeliveryModeChosen: (deliveryMode: DeliveryMode) => void;
}

const Step5BDeliveryModeChoice: React.FC<Step5BDeliveryModeChoiceProps> = ({
  settings,
  onDeliveryModeChosen,
}) => {
  const homeDeliveryLocations = getPickupLocationsForDeliveryMode(
    settings.pickupLocations,
    "home_delivery",
  );

  const deliveryChargeBadge =
    homeDeliveryLocations.length === 1
      ? buildDeliveryChargeBadge(homeDeliveryLocations[0])
      : null;

  return (
    <>
      <p
        dangerouslySetInnerHTML={{
          __html: settings.strings.homeDeliveryChoiceText,
        }}
        className={"text-center"}
      />
      <div className={"d-flex flex-row gap-2"}>
        <TapirButton
          text={"Abholung an einer Verteilstation"}
          variant={BUTTON_VARIANT}
          onClick={() => onDeliveryModeChosen("pickup")}
          icon={"storefront"}
        />
        <TapirButton
          text={
            deliveryChargeBadge ? (
              <>
                Hauslieferung
                <br />
                <small>{deliveryChargeBadge}</small>
              </>
            ) : (
              "Hauslieferung"
            )
          }
          variant={BUTTON_VARIANT}
          onClick={() => onDeliveryModeChosen("home_delivery")}
          icon={"local_shipping"}
        />
      </div>
    </>
  );
};

export default Step5BDeliveryModeChoice;
