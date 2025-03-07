import React, { useEffect, useState } from "react";
import { ListGroup, Modal, Placeholder, Spinner, Table } from "react-bootstrap";
import {
  DeliveriesApi,
  Delivery,
  Joker,
  JokerRestriction,
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
  loadDeliveries: () => void;
  deliveriesLoading: boolean;
}

const ManageJokersModal: React.FC<ManageJokersModalProps> = ({
  onHide,
  show,
  memberId,
  deliveries,
  loadDeliveries,
  deliveriesLoading,
}) => {
  const api = useApi(DeliveriesApi);
  const [jokers, setJokers] = useState<JokerWithCancellationLimit[]>([]);
  const [infoLoading, setInfoLoading] = useState(false);
  const [maxJokersPerGrowingPeriod, setMaxJokersPerGrowingPeriod] =
    useState(-1);
  const [restrictions, setRestrictions] = useState<JokerRestriction[]>([]);
  const [weekdayLimit, setWeekdayLimit] = useState(6);
  const [requestLoading, setRequestLoading] = useState(false);
  const [selectedJokerForCancellation, setSelectedJokerForCancellation] =
    useState<Joker>();
  const [selectedDeliveryForJokerUse, setSelectedDeliveryForJokerUse] =
    useState<Delivery>();

  dayjs.extend(Weekday);
  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  useEffect(() => {
    if (!show) return;

    setInfoLoading(true);
    loadData();
  }, [show, memberId]);

  function loadData() {
    api
      .deliveriesApiMemberJokerInformationRetrieve({ memberId: memberId })
      .then((info) => {
        setJokers(info.usedJokers);
        setMaxJokersPerGrowingPeriod(info.maxJokersPerGrowingPeriod);
        setWeekdayLimit(info.weekdayLimit);
        setRestrictions(info.jokerRestrictions);
      })
      .catch((error) => alert(error))
      .finally(() => setInfoLoading(false));

    loadDeliveries();
  }

  function getWeekdayLimitDisplay() {
    return dayjs().weekday(weekdayLimit).format("dddd");
  }

  function getJokerStatus(delivery: Delivery) {
    if (delivery.jokerUsed) {
      return <span>Joker eingesetzt</span>;
    }

    if (!delivery.canJokerBeUsed) {
      return <span>Joker kann nicht eingesetzt werden</span>;
    }

    return (
      <TapirButton
        text={"Joker einsetzen"}
        variant={"outline-primary"}
        size={"sm"}
        icon={"free_cancellation"}
        disabled={requestLoading}
        loading={selectedDeliveryForJokerUse == delivery}
        onClick={() => useJoker(delivery)}
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
            onClick={() => cancelJoker(jokerWithCancellation.joker)}
            disabled={requestLoading}
            loading={
              jokerWithCancellation.joker == selectedJokerForCancellation
            }
          />
        </td>
      </tr>
    );
  }

  function cancelJoker(joker: Joker) {
    setRequestLoading(true);
    setSelectedJokerForCancellation(joker);
    api
      .deliveriesApiCancelJokerCreate({ jokerId: joker.id })
      .then(() => loadData())
      .catch((error) => alert(error))
      .finally(() => {
        setRequestLoading(false);
        setSelectedJokerForCancellation(undefined);
        loadData();
      });
  }

  function useJoker(delivery: Delivery) {
    setRequestLoading(true);
    setSelectedDeliveryForJokerUse(delivery);
    api
      .deliveriesApiUseJokerCreate({
        memberId: memberId,
        date: delivery.deliveryDate,
      })
      .then(() => loadData())
      .catch((error) => alert(error))
      .finally(() => {
        setRequestLoading(false);
        setSelectedDeliveryForJokerUse(undefined);
        loadData();
      });
  }

  function loadingPlaceholder() {
    return Array.from(Array(7).keys()).map((index) => {
      return (
        <tr key={index}>
          {Array.from(Array(3).keys()).map((index) => {
            return (
              <td key={index}>
                <Placeholder lg={10} />
              </td>
            );
          })}
        </tr>
      );
    });
  }

  return (
    <Modal onHide={onHide} show={show} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>Jokers verwalten</h4>
        </Modal.Title>
      </Modal.Header>
      {infoLoading ? (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      ) : (
        <ListGroup variant="flush">
          <ListGroup.Item>
            Jokers können bis zum {getWeekdayLimitDisplay()} (inklusiv) vor der
            Lieferungstag eingesetzt oder abgesagt werden. <br />
            Es dürfen pro Vertragsjahr {maxJokersPerGrowingPeriod} Jokers
            eingesetzt werden.
            {restrictions.length > 0 && (
              <>
                <br />
                Zusätzliche Einschränkungen:
                <ul>
                  {restrictions.map((restriction, index) => (
                    <li
                      key={restriction.startDay + "-" + restriction.startMonth}
                    >
                      Zwischen dem {restriction.startDay}.
                      {restriction.startMonth}. und dem {restriction.endDay}.
                      {restriction.endMonth}. dürfen maximal{" "}
                      {restriction.maxJokers} Jokers eingesetzt werden.
                    </li>
                  ))}
                </ul>
              </>
            )}
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
                {deliveriesLoading
                  ? loadingPlaceholder()
                  : deliveries.map((delivery) => {
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
      )}
    </Modal>
  );
};

export default ManageJokersModal;
