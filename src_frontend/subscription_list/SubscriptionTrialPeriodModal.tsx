import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import { SubscriptionTrialFields, SubscriptionsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
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

function parseApiDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDateForInput(date: Date | string | null | undefined): string {
  if (!date) {
    return "";
  }
  const parsedDate = typeof date === "string" ? parseApiDate(date) : date;
  const year = parsedDate.getFullYear();
  const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
  const day = String(parsedDate.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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
    if (subscription.effectiveTrialEndDate) {
      return parseApiDate(subscription.effectiveTrialEndDate);
    }
    if (subscription.defaultTrialEndDate) {
      return parseApiDate(subscription.defaultTrialEndDate);
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
              <li>Vertrag: {formatSubscription(subscription)}</li>
              <li>Vertrags-Start: {formatDateNumeric(subscription.startDate)}</li>
              <li>
                Vertrags-Ende:{" "}
                {subscription.endDate
                  ? formatDateNumeric(subscription.endDate)
                  : "—"}
              </li>
            </ul>
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
                label={"Probezeit deaktiviert"}
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
                label={"Individuelles Probezeit-Ende"}
                checked={useCustomEndDate}
                onChange={(event) => {
                  setUseCustomEndDate(event.target.checked);
                  setError(undefined);
                  if (
                    event.target.checked &&
                    !customEndDate &&
                    subscription.trialEndDateOverride
                  ) {
                    setCustomEndDate(
                      formatDateForInput(subscription.trialEndDateOverride),
                    );
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
                    Muss ein Sonntag sein.
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
