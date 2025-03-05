import React, { useEffect, useState } from "react";
import { ListGroup, Modal, Table } from "react-bootstrap";
import {
  DeliveriesApi,
  Delivery,
  GrowingPeriod,
  JokerWithCancellationLimit,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import dayjs from "dayjs";
import "dayjs/locale/de";
import Weekday from "dayjs/plugin/weekday";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import TapirButton from "../components/TapirButton.tsx";
import { formatDateText } from "../utils/formatDateText.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface ManageJokersModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  deliveries: Delivery[];
}

const ManageJokersModal: React.FC<ManageJokersModalProps> = ({
  onHide,
  show,
  memberId,
  deliveries,
}) => {
  const api = useApi(DeliveriesApi);
  const [jokers, setJokers] = useState<JokerWithCancellationLimit[]>([]);
  const [infoLoading, setInfoLoading] = useState(false);
  const [growingPeriods, setGrowingPeriods] = useState<GrowingPeriod[]>([]);
  const [maxJokersPerGrowingPeriod, setMaxJokersPerGrowingPeriod] =
    useState(-1);
  const [weekdayLimit, setWeekdayLimit] = useState(6);

  dayjs.extend(Weekday);
  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  useEffect(() => {
    if (!show) return;

    setInfoLoading(true);
    api
      .deliveriesApiMemberJokerInformationRetrieve({ memberId: memberId })
      .then((info) => {
        setJokers(info.usedJokers);
        setGrowingPeriods(info.growingPeriods);
        setMaxJokersPerGrowingPeriod(info.maxJokersPerGrowingPeriod);
        setWeekdayLimit(info.weekdayLimit);
      })
      .catch((error) => alert(error))
      .finally(() => setInfoLoading(false));
  }, [show, memberId]);

  function getWeekdayLimitDisplay() {
    return dayjs().weekday(weekdayLimit).format("dddd");
  }

  function getJokerStatus(delivery: Delivery) {
    if (delivery.jokerUsed) {
      return <span>Joker eingesetzt</span>;
    }

    if (!delivery.canJokerBeUsed) {
      return <span>Joker kann nicht mehr eingesetzt werden</span>;
    }

    return (
      <TapirButton
        text={"Joker einsetzen"}
        variant={"outline-primary"}
        size={"sm"}
        icon={"free_cancellation"}
      />
    );
  }

  function usedJokersTable() {
    return (
      <Table striped hover responsive>
        <thead>
          <tr>
            <th>KW</th>
            <th>Kann abgesagt werden spätestens am</th>
            <th></th>
          </tr>
        </thead>
        <tbody>{jokers.map(usedJokerLine)}</tbody>
      </Table>
    );
  }

  function usedJokerLine(jokerWithCancellation: JokerWithCancellationLimit) {
    return (
      <tr key={jokerWithCancellation.joker.id}>
        <td>KW{dayjs(jokerWithCancellation.joker.date).week()}</td>
        <td>{formatDateText(jokerWithCancellation.cancellationLimit)}</td>
        <td>
          <TapirButton
            text={"Joker absagen"}
            variant={"outline-primary"}
            size={"sm"}
            icon={"cancel"}
          />
        </td>
      </tr>
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>Jokers verwalten</h4>
        </Modal.Title>
      </Modal.Header>
      <ListGroup variant="flush">
        <ListGroup.Item>
          Jokers können bis zum {getWeekdayLimitDisplay()} (inklusiv) vor der
          Lieferungstag eingesetzt oder abgesagt werden
        </ListGroup.Item>
        <ListGroup.Item>
          <h5>Eingesetzter Jokers</h5>
          {jokers.length == 0
            ? "Noch kein eingesetzte Joker"
            : usedJokersTable()}
        </ListGroup.Item>
        <ListGroup.Item style={{ overflowY: "scroll", maxHeight: "20em" }}>
          <h5>Kommende Lieferungen</h5>
          <Table striped hover responsive>
            <thead>
              <tr>
                <th>KW</th>
                <th>Datum der Lieferung</th>
                <th>Joker Status</th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map((delivery) => {
                return (
                  <tr key={formatDateNumeric(delivery.deliveryDate)}>
                    <td>KW{dayjs(delivery.deliveryDate).week()}</td>
                    <td>{formatDateText(delivery.deliveryDate)}</td>
                    <td>{getJokerStatus(delivery)}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </ListGroup.Item>
      </ListGroup>
    </Modal>
  );
};

export default ManageJokersModal;
