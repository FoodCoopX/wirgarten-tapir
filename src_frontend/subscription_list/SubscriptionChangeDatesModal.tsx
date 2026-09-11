import dayjs from "dayjs";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import React, { useEffect, useState } from "react";
import {
  Alert,
  Col,
  Form,
  ListGroup,
  Modal,
  Row,
  Spinner,
} from "react-bootstrap";
import {
  CoopApi,
  Member,
  PublicSubscription,
  SolidarityContribution,
  SolidarityContributionApi,
  Subscription,
  SubscriptionTrialFields,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatSubscription, {
  formatPublicSubscription,
} from "../utils/formatSubscription.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import SubscriptionChangeDatesWeekInput from "./SubscriptionChangeDatesWeekInput.tsx";

interface SubscriptionChangeDatesModalProps {
  onHide: () => void;
  show: boolean;
  subscriptionId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}
const HEADER_HELP_TEXT = (
  <>
    <p>
      Du kannst hier die Vertragslaufzeiten anpassen. Nutze dieses Pop-Up z.B.
      zum Eintragen von Kulanzkündigungen während der Vertragsperiode.
    </p>
    <p>
      Bitte prüft nach Veränderungen der Vertragslaufzeiten anschließend die
      Zahlungsreihe für das bearbeitete Mitglied. Es ergeben sich ggf.
      Rückzahlungen (z.B. wenn vierteljährlich / halbjährlich / jährlich gezahlt
      wird und somit somit längere Perioden vorbezahlt wurden).
    </p>
    <p>
      Beachte: Das Mitglied erhält keine automatisierte E-Mail nach Einstellung
      der neuen Vertragsdaten.
    </p>
  </>
);

const END_DATE_HELP_TEXT = (
  <>
    <p>
      Das neue Vertragsende-Datum muss immer ein Sonntag sei, wenn du die Option
      "In einer bestimmten KW" wählst. Alternativ kannst du auch das
      Vertragsperioden-Enddatum auswählen.
    </p>
    <p>
      Wenn das neue Vertragsende-Datum vor dem Ende der Vertragsperiode liegt,
      wird der Vertrag als gekündigt markiert und nicht mehr verlängert. Sofern
      der Vertrag bereits auf die neue Vertragsperiode verlängert worden sein,
      wir auch die Verlängerung gelöscht.
    </p>
  </>
);

const OTHER_CONTRACTS_HELP_TEXT = (
  <>
    <p>
      Solidarbeiträge und Verträge die gültig sind am altem oder neuem End-Datum
      bekommen das gleiche End-Datum wie der Vertrag.
    </p>
    <p>Ausgelaufene Solidarbeiträge und Verträge werden nicht geändert.</p>
    <p>
      Solidarbeiträge und Verträge die nach dem neuem End-Datum starten werden
      gelöscht.
    </p>
    <p>
      Je nachdem ob das Mitglied schon vorbezahlt hat können Gutschriften
      entstehen.
    </p>
  </>
);

function isWeekValid(week: number | undefined) {
  if (!week) {
    return false;
  }

  return week >= 1 && week <= 53;
}

const SubscriptionChangeDatesModal: React.FC<
  SubscriptionChangeDatesModalProps
> = ({ onHide, show, subscriptionId, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const solidarityContributionApi = useApi(
    SolidarityContributionApi,
    csrfToken,
  );
  const coopApi = useApi(CoopApi, csrfToken);
  const [mainDataLoading, setMainDataLoading] = useState(true);
  const [extraDataLoading, setExtraDataLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionTrialFields>();
  const [memberId, setMemberId] = useState<string>();
  const [memberData, setMemberData] = useState<Member>();
  const [startWeek, setStartWeek] = useState<number>(1);
  const [endWeek, setEndWeek] = useState<number>();
  const [startDate, setStartDate] = useState<Date>();
  const [endDate, setEndDate] = useState<Date>();
  const [abortController, setAbortController] = useState<AbortController>();
  const [error, setError] = useState<string>();
  const [startDateIsPeriodStart, setStartDateIsPeriodStart] = useState(false);
  const [endDateIsPeriodEnd, setEndDateIsPeriodEnd] = useState(false);
  const [solidarityContributions, setSolidarityContributions] = useState<
    SolidarityContribution[]
  >([]);
  const [updateEndDateOtherContracts, setUpdateEndDateOtherContracts] =
    useState(false);
  const [otherSubscriptions, setOtherSubscriptions] = useState<
    PublicSubscription[]
  >([]);

  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  useEffect(() => {
    if (!show) {
      return;
    }

    subscriptionsApi
      .subscriptionsSubscriptionsRetrieve({ id: subscriptionId })
      .then((subscription) => {
        setSubscription(subscription);
        setMemberId(subscription.member);
      })
      .catch(
        async (error) =>
          await handleRequestError(
            error,
            "Fehler bei der Bestätigung der Bestellung",
            setToastDatas,
          ),
      )
      .finally(() => setMainDataLoading(false));

    setMainDataLoading(true);
  }, [show]);

  useEffect(() => {
    if (!show || !memberId) {
      return;
    }

    setExtraDataLoading(true);

    Promise.all([
      coopApi.coopMembersRetrieve({ id: memberId }),
      subscriptionsApi.subscriptionsApiMemberSubscriptionDataRetrieve({
        memberId: memberId,
      }),
      solidarityContributionApi.solidarityContributionApiMemberSolidarityContributionsRetrieve(
        {
          memberId: memberId,
        },
      ),
    ])
      .then(([memberData, subscriptionData, solidarityData]) => {
        setMemberData(memberData);
        setOtherSubscriptions(
          subscriptionData.subscriptions.filter(
            (otherSubscription) =>
              otherSubscription.productId !== subscription?.product.id,
          ),
        );
        setSolidarityContributions(solidarityData.contributions);
      })
      .catch(
        async (error) =>
          await handleRequestError(
            error,
            "Fehler bei der Laden der zusätzliche DAten",
            setToastDatas,
          ),
      )
      .finally(() => setExtraDataLoading(false));
  }, [memberId, show]);

  useEffect(() => {
    if (!subscription) {
      return;
    }

    setStartWeek(dayjs(subscription.startDate).week());
    if (subscription.endDate) {
      setEndWeek(dayjs(subscription.endDate).week());
    }
  }, [subscription]);

  function onConfirmChange() {
    if (!subscription || !startWeek || !endWeek) {
      return;
    }

    setMainDataLoading(true);

    subscriptionsApi
      .subscriptionsApiDatesChangeCreate({
        subscriptionDateChangeRequestRequest: {
          subscriptionId: subscriptionId,
          startDateIsOnPeriodStart: startDateIsPeriodStart,
          startWeek: startWeek,
          endDateIsOnPeriodEnd: endDateIsPeriodEnd,
          endWeek: endWeek,
          updateEndDateOfOtherContracts: updateEndDateOtherContracts,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          location.reload();
          onHide();
        } else {
          setError(response.error ?? undefined);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim ändern der Vertragsdaten",
          setToastDatas,
        ),
      )
      .finally(() => setMainDataLoading(false));
  }

  useEffect(() => {
    setStartDate(undefined);
    setEndDate(undefined);

    fetchDeliveryDates();
  }, [startWeek, endWeek]);

  function fetchDeliveryDates() {
    if (!subscription || !isWeekValid(startWeek) || !isWeekValid(endWeek)) {
      return;
    }

    if (abortController) {
      abortController.abort();
    }

    const localController = new AbortController();
    setAbortController(localController);

    subscriptionsApi
      .subscriptionsApiConvertWeeksToDateForSubscriptionChangeRetrieve(
        {
          subscriptionId: subscriptionId,
          startWeek: startWeek,
          endWeek: endWeek,
        },
        { signal: localController.signal },
      )
      .then((response) => {
        setStartDate(response.startDate);
        setEndDate(response.endDate);
      })
      .catch(async (error) => {
        if (error.cause?.name === "AbortError") return;
        await handleRequestError(
          error,
          "Fehler beim Laden der Lieferung-Daten",
        );
      });
  }

  function getBodyContent() {
    if (mainDataLoading) {
      return <Spinner />;
    }

    if (subscription === undefined) {
      return <p>Fehler beim Laden der Vertragsdaten</p>;
    }

    return (
      <ListGroup variant="flush">
        <ListGroup.Item>
          <div>
            Aktuelle Vertragsdaten:
            <ul>
              <li>Produkt: {formatSubscription(subscription as Subscription)}</li>
              <li>Start: {formatDateNumeric(subscription.startDate)}</li>
              <li>End: {formatDateNumeric(subscription.endDate)}</li>
              {memberData && (
                <li>
                  Mitglied: {memberData.firstName} {memberData.lastName}{" "}
                  {memberData.memberNo && "#" + memberData.memberNo}
                </li>
              )}
            </ul>
          </div>
        </ListGroup.Item>
        <ListGroup.Item>
          {error && (
            <Row className={"mt-4"}>
              <Col>
                <Alert variant={"danger"}>{error}</Alert>
              </Col>
            </Row>
          )}
          {subscription && (
            <Row>
              <Col>
                <Form.Group>
                  <Form.Label>
                    <span
                      className={"d-flex flex-row gap-2 align-items-center"}
                    >
                      Start-Datum
                      <TapirHelpButton
                        text={
                          'Das neue Vertragsstart-Datum muss immer ein Montag sein, wenn du die Option "In einer bestimmten KW" wählst. Alternativ kannst du das Vertragsperioden-Startdatum auswählen.'
                        }
                        buttonSize={"sm"}
                      />
                    </span>
                  </Form.Label>
                  <Form.Select
                    onChange={(event) =>
                      setStartDateIsPeriodStart(event.target.value === "true")
                    }
                    value={startDateIsPeriodStart ? "true" : "false"}
                    className={"mb-2"}
                  >
                    <option value={"true"}>
                      Am erstem Tag der Vertragsperiode
                    </option>
                    <option value={"false"}>In einer bestimmten KW</option>
                  </Form.Select>
                  {!startDateIsPeriodStart && (
                    <SubscriptionChangeDatesWeekInput
                      week={startWeek}
                      setWeek={setStartWeek}
                      date={startDate}
                    />
                  )}
                </Form.Group>
              </Col>
              <Col>
                <Form.Group>
                  <Form.Label>
                    <span
                      className={"d-flex flex-row gap-2 align-items-center"}
                    >
                      End-Datum
                      <TapirHelpButton
                        text={END_DATE_HELP_TEXT}
                        buttonSize={"sm"}
                      />
                    </span>
                  </Form.Label>
                  <Form.Select
                    onChange={(event) =>
                      setEndDateIsPeriodEnd(event.target.value === "true")
                    }
                    value={endDateIsPeriodEnd ? "true" : "false"}
                    className={"mb-2"}
                  >
                    <option value={"true"}>
                      Am letztem Tag der Vertragsperiode
                    </option>
                    <option value={"false"}>In einer bestimmten KW</option>
                  </Form.Select>
                  {!endDateIsPeriodEnd && (
                    <SubscriptionChangeDatesWeekInput
                      week={endWeek}
                      setWeek={setEndWeek}
                      date={endDate}
                    />
                  )}
                </Form.Group>
              </Col>
            </Row>
          )}
        </ListGroup.Item>
        <ListGroup.Item>
          {extraDataLoading ? (
            <Spinner />
          ) : (
            <>
              <Row>
                <Col>
                  <h6>Weitere Beiträge:</h6>
                </Col>
              </Row>
              {otherSubscriptions.length + solidarityContributions.length >
                0 && (
                <Row>
                  <Col>
                    <Form.Group>
                      <Form.Check
                        id={"soli_end_date"}
                        checked={updateEndDateOtherContracts}
                        onChange={(e) =>
                          setUpdateEndDateOtherContracts(e.target.checked)
                        }
                        label={
                          <span className={"d-flex gap-2"}>
                            <span>
                              Soll das End-Datum für alle weitere Verträge und
                              Solidarbeitrag ebenfalls gesetzt werden?
                            </span>
                            <TapirHelpButton
                              buttonSize={"sm"}
                              text={OTHER_CONTRACTS_HELP_TEXT}
                            />
                          </span>
                        }
                      />
                    </Form.Group>
                  </Col>
                </Row>
              )}
              <Row>
                <Col>
                  <h6>Solidarbeitrag</h6>
                  {solidarityContributions.length === 0 ? (
                    <span>Dieses Mitglied hat kein Solidarbeitrag.</span>
                  ) : (
                    <div>
                      <ul>
                        {solidarityContributions.map((contribution) => (
                          <li key={contribution.id}>
                            {formatCurrency(
                              Number.parseFloat(contribution.amount),
                            )}{" "}
                            von {formatDateNumeric(contribution.startDate)} bis{" "}
                            {formatDateNumeric(contribution.endDate)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Col>
                <Col>
                  <h6>Verträge</h6>
                  {otherSubscriptions.length === 0 ? (
                    "Dieses Mitglied hat kein andere Verträge."
                  ) : (
                    <div>
                      Weitere Verträge dieses Mitglieds:
                      <ul>
                        {otherSubscriptions.map((otherSubscription) => (
                          <li key={otherSubscription.productId}>
                            {formatPublicSubscription(otherSubscription)} vom{" "}
                            {formatDateNumeric(otherSubscription.startDate)} zum{" "}
                            {formatDateNumeric(otherSubscription.endDate)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Col>
              </Row>
            </>
          )}
        </ListGroup.Item>
      </ListGroup>
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <span
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <Modal.Title>Vertragslaufzeit anpassen / Sonderkündigung</Modal.Title>
          <TapirHelpButton text={HEADER_HELP_TEXT} />
        </span>
      </Modal.Header>

      <Modal.Body>{getBodyContent()}</Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Daten ändern"}
          loading={mainDataLoading}
          onClick={onConfirmChange}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default SubscriptionChangeDatesModal;
