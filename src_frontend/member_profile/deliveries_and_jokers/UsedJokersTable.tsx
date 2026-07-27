import dayjs from "dayjs";
import "dayjs/locale/de";
import isSameOrAfter from "dayjs/plugin/isSameOrAfter";
import React from "react";
import { Button, OverlayTrigger, Table, Tooltip } from "react-bootstrap";
import { Joker, JokerWithCancellationLimit } from "../../api-client";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";
import TapirButton from "../../components/TapirButton.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";
import { getWeekdayDisplay } from "../../utils/getWeekdayDisplay.ts";

interface UsedJokersTableProps {
  jokers: JokerWithCancellationLimit[];
  cancelJoker: (joker: Joker) => void;
  requestLoading: boolean;
  selectedJokerForCancellation: Joker | undefined;
  weekdayLimit: number;
  deliveriesLoading: boolean;
}

const UsedJokersTable: React.FC<UsedJokersTableProps> = ({
  jokers,
  requestLoading,
  cancelJoker,
  selectedJokerForCancellation,
  weekdayLimit,
  deliveriesLoading,
}) => {
  dayjs.extend(isSameOrAfter);

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
            {jokers.map((jokerWithCancellation) => (
              <tr key={jokerWithCancellation.joker.id}>
                <td>KW{dayjs(jokerWithCancellation.joker.date).week()}</td>
                <td>{formatDateText(jokerWithCancellation.deliveryDate)}</td>
                <td>
                  {dayjs(jokerWithCancellation.cancellationLimit).isSameOrAfter(
                    new Date(),
                    "day",
                  ) ? (
                    <TapirButton
                      text={"Joker absagen"}
                      variant={"outline-primary"}
                      size={"sm"}
                      icon={"cancel"}
                      onClick={() => cancelJoker(jokerWithCancellation.joker)}
                      disabled={requestLoading}
                      loading={
                        jokerWithCancellation.joker ==
                        selectedJokerForCancellation
                      }
                    />
                  ) : (
                    <OverlayTrigger
                      overlay={
                        <Tooltip
                          id={"tooltip-" + jokerWithCancellation.joker.id}
                        >
                          Du musst bis zum {getWeekdayDisplay(weekdayLimit)}{" "}
                          Mitternacht den Joker absagen
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

export default UsedJokersTable;
