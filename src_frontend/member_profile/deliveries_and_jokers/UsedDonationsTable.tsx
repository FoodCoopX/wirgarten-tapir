import React from "react";
import {
  DeliveryDonation,
  DeliveryDonationWithCancellationLimit,
} from "../../api-client";
import "dayjs/locale/de";
import { Button, OverlayTrigger, Table, Tooltip } from "react-bootstrap";
import dayjs from "dayjs";
import { formatDateText } from "../../utils/formatDateText.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { getWeekdayDisplay } from "../../utils/getWeekdayDisplay.ts";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";

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
    <Table striped hover responsive className={"fixed_header"}>
      <thead>
        <tr>
          <th>KW</th>
          <th>Lieferdatum</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {deliveriesLoading ? (
          <PlaceholderTableRows nbRows={4} nbColumns={3} size={"sm"} />
        ) : (
          <>
            {donations.map((donationWithCancellation) => (
              <tr key={donationWithCancellation.donation.id}>
                <td>
                  KW{dayjs(donationWithCancellation.donation.date).week()}
                </td>
                <td>{formatDateText(donationWithCancellation.deliveryDate)}</td>
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
                          Mitternacht die Spende absagen
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
