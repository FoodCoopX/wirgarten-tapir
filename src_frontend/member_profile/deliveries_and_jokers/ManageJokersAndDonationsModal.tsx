import React, { useEffect, useState } from "react";
import {
  Button,
  Col,
  ListGroup,
  Modal,
  OverlayTrigger,
  Placeholder,
  Row,
  Spinner,
  Table,
  Tooltip,
} from "react-bootstrap";
import {
  DeliveriesApi,
  Delivery,
  DeliveryDonation,
  type DeliveryDonationWithCancellationLimit,
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
import UsedJokersTable from "./UsedJokersTable.tsx";
import UsedDonationsTable from "./UsedDonationsTable.tsx";

interface ManageJokersAndDonationsModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  deliveries: Delivery[];
  loadDeliveries: () => void;
  deliveriesLoading: boolean;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  areJokersEnabled: boolean;
  areDonationsEnabled: boolean;
}

function loadingPlaceholder() {
  return Array.from(new Array(7).keys()).map((index) => {
    return (
      <tr key={index}>
        {Array.from(new Array(3).keys()).map((index) => {
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

const ManageJokersAndDonationsModal: React.FC<
  ManageJokersAndDonationsModalProps
> = ({
  onHide,
  show,
  memberId,
  deliveries,
  loadDeliveries,
  deliveriesLoading,
  csrfToken,
  setToastDatas,
  areJokersEnabled,
  areDonationsEnabled,
}) => {
  const api = useApi(DeliveriesApi, csrfToken);
  const [jokers, setJokers] = useState<JokerWithCancellationLimit[]>([]);
  const [donations, setDonations] = useState<
    DeliveryDonationWithCancellationLimit[]
  >([]);
  const [infoLoading, setInfoLoading] = useState(false);
  const [weekdayLimit, setWeekdayLimit] = useState(6);
  const [requestLoading, setRequestLoading] = useState(false);
  const [selectedJokerForCancellation, setSelectedJokerForCancellation] =
    useState<Joker>();
  const [selectedDonationForCancellation, setSelectedDonationForCancellation] =
    useState<DeliveryDonation>();
  const [selectedDeliveryForJokerUse, setSelectedDeliveryForJokerUse] =
    useState<Delivery>();
  const [selectedDeliveryForDonationUse, setSelectedDeliveryForDonationUse] =
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
        setDonations(info.usedDonations);
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

    if (delivery.donationUsed) {
      return <span>Lieferung gespendet</span>;
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
                id={"tooltip-joker-" + formatDateNumeric(delivery.deliveryDate)}
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

  function getDonationStatus(delivery: Delivery) {
    if (delivery.jokerUsed) {
      return <span>Joker eingesetzt</span>;
    }

    if (delivery.donationUsed) {
      return <span>Lieferung gespendet</span>;
    }

    if (delivery.canDeliveryBeDonated) {
      return (
        <TapirButton
          text={"Lieferung spenden"}
          variant={"outline-primary"}
          size={"sm"}
          icon={"free_cancellation"}
          disabled={requestLoading}
          loading={selectedDeliveryForDonationUse == delivery}
          onClick={() => useDonation(delivery)}
        />
      );
    }

    if (!delivery.canJokerBeUsedRelativeToDateLimit) {
      return (
        <span>
          Lieferung kann nicht mehr gespendet werden{" "}
          <OverlayTrigger
            overlay={
              <Tooltip
                id={
                  "tooltip-donation-" + formatDateNumeric(delivery.deliveryDate)
                }
              >
                Du musst bis zum {getWeekdayLimitDisplay()} Mitternacht die
                Spende setzen
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

    return <span>Spende kann nicht eingesetzt werden</span>;
  }

  function cancelJoker(joker: Joker) {
    setRequestLoading(true);
    setSelectedJokerForCancellation(joker);
    api
      .deliveriesApiCancelJokerCreate({ jokerId: joker.id })
      .then(() => loadData())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Absagen eines Jokers",
          setToastDatas,
        ),
      )
      .finally(() => {
        setRequestLoading(false);
        setSelectedJokerForCancellation(undefined);
        loadData();
      });
  }

  function cancelDonation(donation: DeliveryDonation) {
    setRequestLoading(true);
    setSelectedDonationForCancellation(donation);
    api
      .deliveriesApiCancelDonationCreate({ donationId: donation.id })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Absagen einer Spende",
          setToastDatas,
        ),
      )
      .finally(() => {
        setRequestLoading(false);
        setSelectedDonationForCancellation(undefined);
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
      .catch((error) =>
        handleRequestError(error, "Fehler beim Joker-Einsetzen", setToastDatas),
      )
      .finally(() => {
        setRequestLoading(false);
        setSelectedDeliveryForJokerUse(undefined);
        loadData();
      });
  }

  function useDonation(delivery: Delivery) {
    setRequestLoading(true);
    setSelectedDeliveryForDonationUse(delivery);
    api
      .deliveriesApiUseDonationCreate({
        memberId: memberId,
        date: delivery.deliveryDate,
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Spende-Einsetzen",
          setToastDatas,
        ),
      )
      .finally(() => {
        setRequestLoading(false);
        setSelectedDeliveryForDonationUse(undefined);
        loadData();
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

  function buildRelevantNames() {
    let relevant: string[] = [];
    if (areJokersEnabled) {
      relevant.push("Joker");
    }

    if (areDonationsEnabled) {
      relevant.push("Spenden");
    }

    return relevant.join(" & ");
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"xl"}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>{buildRelevantNames()} verwalten</h4>
        </Modal.Title>
      </Modal.Header>
      {infoLoading ? (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      ) : (
        <ListGroup variant="flush">
          {areJokersEnabled && (
            <ListGroup.Item>
              <p>Überischt deiner Joker:</p>
              <ul>
                {usedJokerInGrowingPeriods.map((usedJokerInGrowingPeriod) => {
                  return (
                    <li
                      key={formatDateNumeric(
                        usedJokerInGrowingPeriod.growingPeriodStart,
                      )}
                    >
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
          )}
          <ListGroup.Item>
            <p>
              {buildRelevantNames()} können bis {getWeekdayLimitDisplay()} 23:59
              Uhr vor Liefertag eingesetzt oder abgesagt werden.{" "}
            </p>
            {areJokersEnabled && buildJokerRestrictions()}
          </ListGroup.Item>
          <ListGroup.Item>
            <Row>
              {areJokersEnabled && (
                <Col>
                  <h5>Eingesetzter Joker</h5>
                  {jokers.length == 0 ? (
                    "Noch kein eingesetzte Joker"
                  ) : (
                    <UsedJokersTable
                      jokers={jokers}
                      cancelJoker={cancelJoker}
                      selectedJokerForCancellation={
                        selectedJokerForCancellation
                      }
                      weekdayLimit={weekdayLimit}
                      requestLoading={requestLoading}
                      deliveriesLoading={deliveriesLoading}
                    />
                  )}
                </Col>
              )}
              {areDonationsEnabled && (
                <Col>
                  <h5>Spenden</h5>
                  {donations.length == 0 ? (
                    "Keine Lieferung gespendet"
                  ) : (
                    <UsedDonationsTable
                      donations={donations}
                      selectedDonationForCancellation={
                        selectedDonationForCancellation
                      }
                      requestLoading={requestLoading}
                      weekdayLimit={weekdayLimit}
                      cancelDonation={cancelDonation}
                      deliveriesLoading={deliveriesLoading}
                    />
                  )}
                </Col>
              )}
            </Row>
          </ListGroup.Item>
          <ListGroup.Item style={{ overflowY: "scroll", maxHeight: "20em" }}>
            <h5>Kommende Lieferungen</h5>
            <Table striped hover responsive className={"fixed_header"}>
              <thead>
                <tr>
                  <th>KW</th>
                  <th>Lieferdatum</th>
                  {areJokersEnabled && <th>Joker Status</th>}
                  {areDonationsEnabled && <th>Spende Status</th>}
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
                          {areJokersEnabled && (
                            <td className={"text-wrap"}>
                              {getJokerStatus(delivery)}
                            </td>
                          )}
                          {areDonationsEnabled && (
                            <td className={"text-wrap"}>
                              {getDonationStatus(delivery)}
                            </td>
                          )}
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

export default ManageJokersAndDonationsModal;
