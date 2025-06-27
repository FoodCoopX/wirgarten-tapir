import React, { Fragment } from "react";
import BestellWizardCardSubtitle from "./BestellWizardCardSubtitle.tsx";
import { Table } from "react-bootstrap";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../utils/formatOpeningTimes.ts";
import { PublicPickupLocation } from "../../api-client";

interface SummaryPickupLocationsProps {
  selectedPickupLocations: PublicPickupLocation[];
  waitingListModeEnabled: boolean;
}

const SummaryPickupLocations: React.FC<SummaryPickupLocationsProps> = ({
  selectedPickupLocations,
  waitingListModeEnabled,
}) => {
  return (
    <div className={"mt-4"}>
      {waitingListModeEnabled ? (
        <BestellWizardCardSubtitle text={"Deine Verteilstationswünsche"} />
      ) : (
        <BestellWizardCardSubtitle text={"Deine Verteilstation"} />
      )}
      <Table bordered={true}>
        <tbody>
          {selectedPickupLocations.map((pickupLocation, index) => (
            <Fragment key={pickupLocation.id!}>
              {waitingListModeEnabled && (
                <tr>
                  <th colSpan={2}>{index + 1}. Wunsch</th>
                </tr>
              )}
              <tr>
                <td>Adresse</td>
                <td>
                  {pickupLocation.name} <br />
                  {formatAddress(
                    pickupLocation.street,
                    pickupLocation.street2,
                    pickupLocation.postcode,
                    pickupLocation.city,
                  )}
                </td>
              </tr>
              <tr>
                <td>Öffnungszeiten</td>
                <td>{formatOpeningTimes(pickupLocation)}</td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </Table>
    </div>
  );
};

export default SummaryPickupLocations;
