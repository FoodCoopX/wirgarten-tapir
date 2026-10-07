import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import {
  Subscription,
  SubscriptionsApi,
  SubscriptionTrialFields,
} from "../api-client";
import { DAY_LABELS } from "../bakery/utils/weekdays.ts";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatSubscription from "../utils/formatSubscription.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface SubscriptionTrialPeriodModalProps {
  onHide: () => void;
  show: boolean;
  subscriptionId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

function formatDateForInput(date: Date | null | undefined): string {
  if (!date) {
    return "";
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const SUNDAY = 6;

function buildCancellationRuleText(subscription: SubscriptionTrialFields) {
  if (!subscription.trialPeriodIsFlexible) {
    return "Kündigt das Mitglied in der Probezeit, endet der Vertrag immer am gewählten Sonntag, egal an welchem Tag es kündigt.";
  }

  const weekdayLimit = subscription.weekdayLimitForDeliveryChanges;
  if (weekdayLimit === SUNDAY || weekdayLimit <= subscription.deliveryWeekday) {
    return "Kündigt das Mitglied in der Probezeit, endet der Vertrag am Sonntag der Woche, in der es kündigt. Die Lieferung dieser Woche erhält es noch, danach keine mehr.";
  }

  // The limit for changes is after the delivery day: once it has passed, next week's delivery is already being prepared.
  const weekdayLimitLabel = DAY_LABELS[weekdayLimit];
  return (
    "Kündigt das Mitglied bis " +
    weekdayLimitLabel +
    " um 23:59 Uhr, endet der Vertrag am Sonntag derselben Woche. Kündigt es später, endet er erst am Sonntag der Folgewoche. Grund: Nach " +
    weekdayLimitLabel +
    " 23:59 Uhr (Kommissioniervariable) sind die Kommissionier-Listen für die Folgewoche erstellt. Diese Lieferung wird noch gepackt und kann abgeholt werden."
  );
}

function buildHelpTextTrialDisabled() {
  return (
    <>
      <p>Mit Klick auf die Checkbox hat dieser Vertrag keine Probezeit.</p>
      <p>Das bedeutet:</p>
      <ul>
        <li>
          Das Mitglied kann den Vertrag nur noch regulär zum Vertragsende und
          mit der normalen Kündigungsfrist kündigen.
        </li>
        <li>
          Die Zahlungen für diesen Vertrag werden wie bei einem regulären
          Vertrag fällig, nicht mehr als Probezeit-Zahlung im Folgemonat.
        </li>
      </ul>
      <p>
        Ein zuvor eingestelltes individuelles Probezeit-Ende wird dabei
        gelöscht.
      </p>
    </>
  );
}

function buildHelpTextCustomEndDate(subscription: SubscriptionTrialFields) {
  return (
    <>
      <p>
        Mit Klick auf die Checkbox kannst du ein individuelles Probezeit-Ende
        für diesen Vertrag einstellen. Das Datum muss ein Sonntag sein.
      </p>
      <p>So wirkt das Datum:</p>
      <ul>
        <li>
          Bis zum gewählten Sonntag um 23:59 Uhr ist der Vertrag in der
          Probezeit. Ab dem Montag danach gilt er als regulärer Vertrag.
        </li>
        <li>{buildCancellationRuleText(subscription)}</li>
      </ul>
      <p>Beachte:</p>
      <ul>
        <li>
          Liegt das Datum in der Vergangenheit, ist die Probezeit sofort
          beendet.
        </li>
        <li>
          Für die Zahlungen zählt der Monatserste: Ist der Vertrag am 1. eines
          Monats noch in der Probezeit, wird dieser Monat als Probezeit-Zahlung
          im Folgemonat fällig. Verschiebst du das Ende in einen anderen Monat,
          kann sich die Fälligkeit ändern.
        </li>
      </ul>
    </>
  );
}

const SubscriptionTrialPeriodModal: React.FC<
  SubscriptionTrialPeriodModalProps
> = ({ onHide, show, subscriptionId, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionTrialFields>();
  const [trialDisabled, setTrialDisabled] = useState(false);
  const [useCustomEndDate, setUseCustomEndDate] = useState(false);
  const [customEndDate, setCustomEndDate] = useState("");
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);
    setError(undefined);

    subscriptionsApi
      .subscriptionsSubscriptionsRetrieve({ id: subscriptionId })
      .then((subscriptionData) => {
        setSubscription(subscriptionData);
        setTrialDisabled(subscriptionData.trialDisabled ?? false);
        setUseCustomEndDate(subscriptionData.trialEndDateOverride != null);
        setCustomEndDate(
          formatDateForInput(subscriptionData.trialEndDateOverride),
        );
      })
      .catch(
        async (requestError) =>
          await handleRequestError(
            requestError,
            "Fehler beim Laden der Probezeit-Daten",
            setToastDatas,
          ),
      )
      .finally(() => setLoading(false));
  }, [show, subscriptionId]);

  function getDisplayedTrialEndDate(): Date | null {
    if (trialDisabled || !subscription) {
      return null;
    }
    if (useCustomEndDate && customEndDate) {
      return new Date(customEndDate);
    }
    if (subscription.defaultTrialEndDate) {
      return new Date(subscription.defaultTrialEndDate);
    }
    return null;
  }

  function onConfirmChange() {
    if (!subscription) {
      return;
    }

    let trialEndDateOverride: Date | null = null;
    if (!trialDisabled && useCustomEndDate) {
      if (!customEndDate) {
        setError("Bitte ein Probezeit-Enddatum angeben.");
        return;
      }
      trialEndDateOverride = new Date(customEndDate);
    }

    setLoading(true);
    setError(undefined);

    subscriptionsApi
      .subscriptionsApiSubscriptionTrialChangeCreate({
        subscriptionTrialChangeRequestRequest: {
          subscriptionId,
          trialDisabled,
          trialEndDateOverride,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          location.reload();
          onHide();
        } else {
          setError(response.error!);
        }
      })
      .catch((requestError) =>
        handleRequestError(
          requestError,
          "Fehler beim Speichern der Probezeit",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function getBodyContent() {
    if (loading) {
      return <Spinner />;
    }

    if (subscription === undefined) {
      return <p>Fehler beim Laden der Probezeit-Daten</p>;
    }

    const displayedTrialEndDate = getDisplayedTrialEndDate();

    return (
      <>
        <Row className={"mb-3"}>
          <Col>
            <ul>
              <li>
                Vertrag: {formatSubscription(subscription as Subscription)}
              </li>
              <li>
                Vertrags-Start: {formatDateNumeric(subscription.startDate)}
              </li>
              <li>
                Vertrags-Ende:{" "}
                {subscription.endDate
                  ? formatDateNumeric(subscription.endDate)
                  : "—"}
              </li>
            </ul>
            <p>
              Die Probezeit gilt pro Vertrag. Hat das Mitglied mehrere Verträge
              (z. B. Zusatzabo oder Solidarbeitrag), behalten diese ihre eigene
              Probezeit.
            </p>
            <p>
              Standardmäßig beginnt die Probezeit am Montag der ersten
              Lieferwoche und endet nach der eingestellten Anzahl Wochen an
              einem Sonntag.
            </p>
            <p>
              Eine Änderung der Probezeit wird sofort in der Datenbank
              hinterlegt und damit wirksam. Das Mitglied bekommt dazu keine
              E-Mail.
            </p>
          </Col>
        </Row>
        {error && (
          <Row className={"mb-3"}>
            <Col>
              <Alert variant={"danger"}>{error}</Alert>
            </Col>
          </Row>
        )}
        <Row>
          <Col>
            <Form.Group className={"mb-3"}>
              <Form.Check
                id={"trial_disabled"}
                label={
                  <span className={"d-flex gap-2"}>
                    <span>Probezeit deaktiviert</span>
                    <TapirHelpButton
                      text={buildHelpTextTrialDisabled()}
                      buttonSize={"sm"}
                    />
                  </span>
                }
                checked={trialDisabled}
                onChange={(event) => {
                  setTrialDisabled(event.target.checked);
                  if (event.target.checked) {
                    setUseCustomEndDate(false);
                  }
                  setError(undefined);
                }}
              />
            </Form.Group>
          </Col>
        </Row>
        {!trialDisabled && (
          <Row className={"mb-3"}>
            <Col>
              <p>
                Ende der Probezeit:{" "}
                {displayedTrialEndDate
                  ? formatDateNumeric(displayedTrialEndDate)
                  : "—"}
              </p>
              <Form.Check
                id={"use_custom_trial_end"}
                label={
                  <span className={"d-flex gap-2"}>
                    <span>Individuelles Probezeit-Ende</span>
                    <TapirHelpButton
                      buttonSize={"sm"}
                      text={buildHelpTextCustomEndDate(subscription)}
                    />
                  </span>
                }
                checked={useCustomEndDate}
                onChange={(event) => {
                  const checked = event.target.checked;
                  setUseCustomEndDate(checked);
                  setError(undefined);
                  if (checked) {
                    if (!customEndDate && subscription.trialEndDateOverride) {
                      setCustomEndDate(
                        formatDateForInput(subscription.trialEndDateOverride),
                      );
                    }
                  } else {
                    setCustomEndDate("");
                  }
                }}
              />
              {useCustomEndDate && (
                <>
                  <Form.Control
                    type={"date"}
                    className={"mt-2"}
                    value={customEndDate}
                    onChange={(event) => {
                      setCustomEndDate(event.target.value);
                      setError(undefined);
                    }}
                  />
                  <Form.Text className={"text-muted"}>
                    Muss ein Sonntag sein. Die Probezeit gilt bis zu diesem Tag
                    um 23:59 Uhr.
                  </Form.Text>
                </>
              )}
            </Col>
          </Row>
        )}
      </>
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Probezeit anpassen</Modal.Title>
      </Modal.Header>
      <Modal.Body>{getBodyContent()}</Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Speichern"}
          loading={loading}
          onClick={onConfirmChange}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default SubscriptionTrialPeriodModal;
