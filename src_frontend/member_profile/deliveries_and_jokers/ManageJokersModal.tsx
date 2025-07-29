import React, { useEffect, useState } from "react";
import {
  Button,
  ListGroup,
  Modal,
  OverlayTrigger,
  Placeholder,
  Spinner,
  Table,
  Tooltip,
} from "react-bootstrap";
import {
  DeliveriesApi,
  Delivery,
  Joker,
  JokerWithCancellationLimit,
  UsedJokerInGrowingPeriod,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import dayjs from "dayjs";
import "dayjs/locale/de";
import Weekday from "dayjs/plugin/weekday";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import TapirButton from "../../components/TapirButton.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

import "../../fixed_header.css";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ToastData } from "../../types/ToastData.ts";

interface ManageJokersModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  deliveries: Delivery[];
  loadDeliveries: () => void;
  deliveriesLoading: boolean;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const ManageJokersModal: React.FC<ManageJokersModalProps> = ({
  onHide,
  show,
  memberId,
  deliveries,
  loadDeliveries,
  deliveriesLoading,
  csrfToken,
  setToastDatas,
}) => {
  const api = useApi(DeliveriesApi, csrfToken);
  const [jokers, setJokers] = useState<JokerWithCancellationLimit[]>([]);
  const [infoLoading, setInfoLoading] = useState(false);
  const [weekdayLimit, setWeekdayLimit] = useState(6);
  const [requestLoading, setRequestLoading] = useState(false);
  const [selectedJokerForCancellation, setSelectedJokerForCancellation] =
    useState<Joker>();
  const [selectedDeliveryForJokerUse, setSelectedDeliveryForJokerUse] =
    useState<Delivery>();
  const [usedJokerInGrowingPeriods, setUsedJokerInGrowingPeriods] = useState<
    UsedJokerInGrowingPeriod[]
  >([]);

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
        setWeekdayLimit(info.weekdayLimit);
        setUsedJokerInGrowingPeriods(info.usedJokerInGrowingPeriod);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Joker-Daten",
          setToastDatas,
        ),
      )
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

    if (delivery.canJokerBeUsed) {
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

    if (!delivery.canJokerBeUsedRelativeToDateLimit) {
      return (
        <span>
          Joker kann nicht mehr eingesetzt werden{" "}
          <OverlayTrigger
            overlay={
              <Tooltip
                id={"tooltip-" + formatDateNumeric(delivery.deliveryDate)}
              >
                Du musst bis zum {getWeekdayLimitDisplay()} Mitternacht den
                Joker setzen
              </Tooltip>
            }
          >
            <Button size={"sm"} variant={"outline-secondary"}>
              <span className={"material-icons"} style={{ fontSize: "16px" }}>
                info
              </span>
            </Button>
          </OverlayTrigger>
        </span>
      );
    }

    if (delivery.isDeliveryCancelledThisWeek) {
      return <span>Keine Lieferung in dieser Woche</span>;
    }

    return <span>Joker kann nicht eingesetzt werden</span>;
  }

  function usedJokersTable() {
    return (
      <Table striped hover responsive className={"fixed_header"}>
        <thead>
          <tr>
            <th>KW</th>
            <th>Lieferdatum</th>
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
        <td>{formatDateText(jokerWithCancellation.deliveryDate)}</td>
        <td>
          {jokerWithCancellation.cancellationLimit >= new Date() ? (
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
          ) : (
            <OverlayTrigger
              overlay={
                <Tooltip id={"tooltip-" + jokerWithCancellation.joker.id}>
                  Du musst bis zum {getWeekdayLimitDisplay()} Mitternacht den
                  Joker absagen
                </Tooltip>
              }
            >
              <Button size={"sm"} variant={"outline-secondary"}>
                <span className={"material-icons"} style={{ fontSize: "16px" }}>
                  info
                </span>
              </Button>
            </OverlayTrigger>
          )}
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
      .catch((error) =>
        handleRequestError(error, "Fehler beim Absagen", setToastDatas),
      )
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
      .catch((error) =>
        handleRequestError(error, "Fehler beim Einsetzen", setToastDatas),
      )
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

  function buildJokerRestrictions() {
    let atLeastOneRestriction = false;
    for (const growingPeriodInfos of usedJokerInGrowingPeriods) {
      if (growingPeriodInfos.jokerRestrictions.length > 0) {
        atLeastOneRestriction = true;
      }
    }
    if (!atLeastOneRestriction) {
      return <></>;
    }

    return (
      <p>
        Es gibt zusätzliche Einschränkungen in der folgende Perioden:
        <ul>
          {usedJokerInGrowingPeriods.map(buildJokerRestrictionForGrowingPeriod)}
        </ul>
      </p>
    );
  }

  function buildJokerRestrictionForGrowingPeriod(
    growingPeriodInfos: UsedJokerInGrowingPeriod,
  ) {
    if (growingPeriodInfos.jokerRestrictions.length <= 0) {
      return <></>;
    }

    return (
      <li>
        Vertragsjahr {formatDateNumeric(growingPeriodInfos.growingPeriodStart)}{" "}
        bis {formatDateNumeric(growingPeriodInfos.growingPeriodEnd)}
        {":"}
        <ul>
          {growingPeriodInfos.jokerRestrictions.map((restriction) => {
            return (
              <li key={restriction.startDay + "-" + restriction.startMonth}>
                {restriction.startDay}.{restriction.startMonth}. bis{" "}
                {restriction.endDay}.{restriction.endMonth}.: maximal{" "}
                {restriction.maxJokers} Joker.
              </li>
            );
          })}
        </ul>
      </li>
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>Joker verwalten</h4>
        </Modal.Title>
      </Modal.Header>
      {infoLoading ? (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      ) : (
        <ListGroup variant="flush">
          <ListGroup.Item>
            <p>Überischt deiner Joker:</p>
            <ul>
              {usedJokerInGrowingPeriods.map((usedJokerInGrowingPeriod) => {
                return (
                  <li>
                    Vertragsjahr{" "}
                    {formatDateNumeric(
                      usedJokerInGrowingPeriod.growingPeriodStart,
                    )}{" "}
                    bis{" "}
                    {formatDateNumeric(
                      usedJokerInGrowingPeriod.growingPeriodEnd,
                    )}
                    {": "}
                    {usedJokerInGrowingPeriod.numberOfUsedJokers} von{" "}
                    {usedJokerInGrowingPeriod.maxJokers} Joker eingesetzt.
                  </li>
                );
              })}
            </ul>
          </ListGroup.Item>
          <ListGroup.Item>
            <p>
              Joker können bis {getWeekdayLimitDisplay()} 23:59 Uhr vor
              Liefertag eingesetzt oder abgesagt werden.{" "}
            </p>
            {buildJokerRestrictions()}
          </ListGroup.Item>

          <ListGroup.Item>
            <h5>Eingesetzter Joker</h5>
            {jokers.length == 0
              ? "Noch kein eingesetzte Joker"
              : usedJokersTable()}
          </ListGroup.Item>
          <ListGroup.Item style={{ overflowY: "scroll", maxHeight: "20em" }}>
            <h5>Kommende Lieferungen</h5>
            <Table striped hover responsive className={"fixed_header"}>
              <thead>
                <tr>
                  <th>KW</th>
                  <th>Lieferdatum</th>
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
