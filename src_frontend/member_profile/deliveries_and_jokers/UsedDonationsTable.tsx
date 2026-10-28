import dayjs from "dayjs";
import "dayjs/locale/de";
import React from "react";
import { Button, OverlayTrigger, Table, Tooltip } from "react-bootstrap";
import {
  DeliveryDonation,
  DeliveryDonationWithCancellationLimit,
} from "../../api-client";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";
import TapirButton from "../../components/TapirButton.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";
import { getWeekdayDisplay } from "../../utils/getWeekdayDisplay.ts";

interface UsedDonationsTableProps {
  donations: DeliveryDonationWithCancellationLimit[];
  cancelDonation: (donation: DeliveryDonation) => void;
  requestLoading: boolean;
  selectedDonationForCancellation: DeliveryDonation | undefined;
  weekdayLimit: number;
  deliveriesLoading: boolean;
}

const UsedDonationsTable: React.FC<UsedDonationsTableProps> = ({
  donations,
  requestLoading,
  cancelDonation,
  selectedDonationForCancellation,
  weekdayLimit,
  deliveriesLoading,
}) => {
  return (
    <Table striped hover responsive size={"sm"}>
      <thead>
        <tr>
          <th>Lieferdatum</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {deliveriesLoading ? (
          <PlaceholderTableRows nbRows={4} nbColumns={2} size={"sm"} />
        ) : (
          <>
            {donations.map((donationWithCancellation) => (
              <tr key={donationWithCancellation.donation.id}>
                <td>
                  {formatDateText(donationWithCancellation.deliveryDate)}
                  <br />
                  <small>
                    KW{dayjs(donationWithCancellation.donation.date).week()}
                  </small>
                </td>
                <td>
                  {donationWithCancellation.cancellationLimit >= new Date() ? (
                    <TapirButton
                      text={"Spende absagen"}
                      variant={"outline-primary"}
                      size={"sm"}
                      icon={"cancel"}
                      onClick={() =>
                        cancelDonation(donationWithCancellation.donation)
                      }
                      disabled={requestLoading}
                      loading={
                        donationWithCancellation.donation ==
                        selectedDonationForCancellation
                      }
                    />
                  ) : (
                    <OverlayTrigger
                      overlay={
                        <Tooltip
                          id={
                            "tooltip-donation" +
                            donationWithCancellation.donation.id
                          }
                        >
                          Du musst bis zum {getWeekdayDisplay(weekdayLimit)}{" "}
                          Mitternacht die Spende absagen.
                        </Tooltip>
                      }
                    >
                      <Button size={"sm"} variant={"outline-secondary"}>
                        <span
                          className={"material-icons"}
                          style={{ fontSize: "16px" }}
                        >
                          info
                        </span>
                      </Button>
                    </OverlayTrigger>
                  )}
                </td>
              </tr>
            ))}
          </>
        )}
      </tbody>
    </Table>
  );
};

export default UsedDonationsTable;
