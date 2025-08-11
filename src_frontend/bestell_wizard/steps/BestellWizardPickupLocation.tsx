import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, Row } from "react-bootstrap";
import {
  PublicPickupLocation,
  WaitingListEntryDetails,
} from "../../api-client";

import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";
import PickupLocationSelector from "../components/PickupLocationSelector.tsx";
import PickupLocationWaitingListSelector from "../components/PickupLocationWaitingListSelector.tsx";

interface BestellWizardPickupLocationProps {
  theme: TapirTheme;
  pickupLocations: PublicPickupLocation[];
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (
    selectedPickupLocations: PublicPickupLocation[],
  ) => void;
  waitingListModeEnabled: boolean;
  pickupLocationsWithCapacityCheckLoading: Set<PublicPickupLocation>;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  firstDeliveryDatesByProductType: { [key: string]: Date };
  waitingListLinkConfirmationModeEnabled: boolean;
  waitingListEntryDetails?: WaitingListEntryDetails;
  trialPeriodLengthInWeeks: number;
}

const BestellWizardPickupLocation: React.FC<
  BestellWizardPickupLocationProps
> = ({
  theme,
  pickupLocations,
  selectedPickupLocations,
  setSelectedPickupLocations,
  waitingListModeEnabled,
  pickupLocationsWithCapacityCheckLoading,
  pickupLocationsWithCapacityFull,
  firstDeliveryDatesByProductType,
  waitingListEntryDetails,
  waitingListLinkConfirmationModeEnabled,
  trialPeriodLengthInWeeks,
}) => {
  function getEarliestDeliveryDate() {
    return Object.values(firstDeliveryDatesByProductType).sort(
      (a, b) => a.getTime() - b.getTime(),
    )[0];
  }

  function shouldShowDeliveryInfo() {
    if (waitingListLinkConfirmationModeEnabled) return true;

    if (waitingListModeEnabled) return false;

    return !(
      selectedPickupLocations.length > 0 &&
      pickupLocationsWithCapacityFull.has(selectedPickupLocations[0])
    );
  }

  return (
    <>
      <Row>
        <Col>
          <BestellWizardCardTitle text={"Deine Verteilstation"} />
          <BestellWizardCardSubtitle text={"Wähle deine Verteilstation"} />
          <p>
            Jede Woche wird dein Ernteanteil an eine Verteilstation deiner Wahl
            geliefert. Du kannst deine Station während der Vertragslaufzeit auch
            wechseln, z.B. wenn du umziehst oder Freunde deinen Anteil abholen.
          </p>
          {waitingListModeEnabled ? (
            <p>
              Bitte wähle deine Wunschverteilstationen. Sobald dort ein Platz
              frei wird, melden wir uns bei dir.
            </p>
          ) : (
            <p>
              Ausgegraute Stationen sind derzeit komplett belegt. Du kannst dich
              auf die Warteliste setzen lassen. Erst wenn ein Mitglied hier
              kündigt, wird wieder ein Platz frei.{" "}
            </p>
          )}
        </Col>
      </Row>
      {waitingListModeEnabled && (
        <PickupLocationWaitingListSelector
          selectedPickupLocations={selectedPickupLocations}
          setSelectedPickupLocations={setSelectedPickupLocations}
          pickupLocations={pickupLocations}
          pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
        />
      )}
      <PickupLocationSelector
        pickupLocations={pickupLocations}
        selectedPickupLocations={selectedPickupLocations}
        setSelectedPickupLocations={setSelectedPickupLocations}
        waitingListModeEnabled={waitingListModeEnabled}
        pickupLocationsWithCapacityCheckLoading={
          pickupLocationsWithCapacityCheckLoading
        }
        pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
        waitingListLinkConfirmationModeEnabled={
          waitingListLinkConfirmationModeEnabled
        }
      />
      {shouldShowDeliveryInfo() && (
        <Row className={"mt-4"}>
          {waitingListEntryDetails &&
          (waitingListEntryDetails.productWishes ?? []).length == 0 ? (
            <p>
              Du holst ab dem {formatDateText(getEarliestDeliveryDate())} an
              deinem neuen Abholort ab
            </p>
          ) : (
            <>
              <BestellWizardCardSubtitle text={"Deine erste Lieferung"} />
              <p>
                Dein erster Ernteanteil kann an dieser Station am{" "}
                {formatDateText(getEarliestDeliveryDate())} geliefert werden.
              </p>
              <p>
                Alle weiteren Informationen zur Lieferung des ersten
                Ernteanteils werden an deine angegebene E-Mail-Adresse versandt.
                Bitte überprüfe ggf. deinen Spam-Ordner.
              </p>
              <p>
                Deine {trialPeriodLengthInWeeks}-wöchige Probezeit beginnt erst,
                nachdem du die erste Lieferung erhalten hast. Während der
                Probezeit besteht keine Kündigungsfrist und Du kannst Deinen
                Ernteanteil wöchentlich jeweils zum Freitag der Vorwoche
                kündigen. Du zahlst nur die Anteile, die du erhalten hast. Nach
                der Probezeit ist eine Kündigung nur zum Jahresende möglich.
              </p>
            </>
          )}
        </Row>
      )}
    </>
  );
};

export default BestellWizardPickupLocation;
