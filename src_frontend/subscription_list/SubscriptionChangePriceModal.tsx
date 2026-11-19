import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import {
  CoopApi,
  Member,
  Subscription,
  SubscriptionTrialFields,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatSubscription from "../utils/formatSubscription.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface SubscriptionChangePriceModalProps {
  onHide: () => void;
  show: boolean;
  subscriptionId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

type PriceMode =
  | "standard"
  | "custom"
  | "free"
  | "bidding_round_bid"
  | "bidding_round_auto_renewed";
const BIDDING_ROUND_MODES = new Set<PriceMode>([
  "bidding_round_bid",
  "bidding_round_auto_renewed",
]);
const ALL_MODES: PriceMode[] = [
  "standard",
  "custom",
  "free",
  ...BIDDING_ROUND_MODES,
];

function isBiddingRoundMode(mode: PriceMode) {
  return BIDDING_ROUND_MODES.has(mode);
}

function getPriceModeDisplay(mode: PriceMode) {
  switch (mode) {
    case "standard":
      return "Standardbetrag";
    case "custom":
      return "Personalisierter Betrag";
    case "free":
      return "Beitragsbefreit";
    case "bidding_round_bid":
      return "Bietrunde: Gebot";
    case "bidding_round_auto_renewed":
      return "Bietrunde: Auto-Verlängert";
  }
}

function getHelpText(mode: PriceMode) {
  switch (mode) {
    case "standard":
      return "Der Vertrag läuft zu dem Preis, welcher in der Konfiguration hinterlegt ist.";
    case "custom":
      return 'Bitte wähle die Höhe des Beitrages für den Vertrag im Textfeld aus. Die Abweichung vom eigentlichen Richtpreis verändert die Berechnung des Solidartopfes nicht. Du kannst unter "Mitglieder" gezielt nach Mitgliedern mit Verträgen mit personalisierten Beträgen suchen.';
    case "free":
      return 'Der Vertrag läuft ohne Beitrag. Dies verringert aber nicht den Solidar-Topf. Du kannst unter "Mitglieder" gezielt nach Mitgliedern mit beitragsbefreiten Verträgensuchen.';
    case "bidding_round_bid":
      return "Der Vertrag läuft zum Bietrundenbetrag. Die Differenz zum individuellen Gebot wird als Solidaritätsbeitrag gebucht. Dieser Modus wird durch die Bietrunde gesetzt und kann nicht manuell gewählt werden.";
    case "bidding_round_auto_renewed":
      return "Der Vertrag wurde automatisch verlängert. Der Vertragspreis ist mindestens der Non-Bidder-Floor; ein höherer bisheriger Betrag bleibt als Bestandsschutz erhalten. Dieser Modus wird durch die Bietrunde gesetzt und kann nicht manuell gewählt werden.";
  }
}

function getMode(subscription: SubscriptionTrialFields): PriceMode {
  if (subscription.priceMode === "bidding_round_bid") {
    return "bidding_round_bid";
  }
  if (subscription.priceMode === "bidding_round_auto_renewed") {
    return "bidding_round_auto_renewed";
  }
  const override = subscription.priceOverride;
  if (override === null || override === undefined) {
    return "standard";
  }
  if (Number.parseFloat(override) === 0) {
    return "free";
  }
  return "custom";
}

const SubscriptionChangePriceModal: React.FC<
  SubscriptionChangePriceModalProps
> = ({ onHide, show, subscriptionId, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionTrialFields>();
  const [memberId, setMemberId] = useState<string>();
  const [memberData, setMemberData] = useState<Member>();
  const [error, setError] = useState<string>();
  const [customPrice, setCustomPrice] = useState("");
  const [priceMode, setPriceMode] = useState<PriceMode>("standard");

  useEffect(() => {
    if (!show) {
      return;
    }

    subscriptionsApi
      .subscriptionsSubscriptionsRetrieve({ id: subscriptionId })
      .then((subscription) => {
        setSubscription(subscription);
        setMemberId(subscription.member);
        setCustomPrice(
          subscription.priceOverride
            ? subscription.priceOverride.toString()
            : "",
        );
        setPriceMode(getMode(subscription));
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler bei der Bestätigung der Bestellung",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));

    setLoading(true);
  }, [show]);

  useEffect(() => {
    if (!show || !memberId) {
      return;
    }

    coopApi
      .coopMembersRetrieve({ id: memberId })
      .then(setMemberData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden des Mitglieds",
          setToastDatas,
        ),
      );
  }, [memberId, show]);

  function onConfirmChange() {
    if (!subscription) {
      return;
    }

    let newPrice: number | null;
    switch (priceMode) {
      case "standard":
        newPrice = null;
        break;
      case "custom": {
        const parsedPrice = Number.parseFloat(customPrice);
        if (Number.isNaN(parsedPrice)) {
          setError("Ungültiger Zahl");
          return;
        }
        newPrice = parsedPrice;
        break;
      }
      case "free":
        newPrice = 0;
        break;
      case "bidding_round_bid":
      case "bidding_round_auto_renewed":
        newPrice = subscription.priceOverride
          ? Number.parseFloat(subscription.priceOverride)
          : null;
        break;
    }

    setLoading(true);

    subscriptionsApi
      .subscriptionsApiSubscriptionPriceOverrideCreate({
        subscriptionPriceOverrideChangeRequestRequest: {
          subscriptionId: subscriptionId,
          priceOverride: newPrice,
          priceMode: priceMode,
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
          "Fehler beim ändern der Vertragspreis",
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
      return <p>Fehler beim Laden der Vertragsdaten</p>;
    }

    return (
      <>
        <Row>
          <Col>
            <div>
              Aktuelle Vertragsdaten:
              <ul>
                <li>
                  Produkt: {formatSubscription(subscription as Subscription)}
                </li>
                <li>Start: {formatDateNumeric(subscription.startDate)}</li>
                <li>End: {formatDateNumeric(subscription.endDate)}</li>
                {memberData && (
                  <li>
                    Mitglied: {memberData.firstName} {memberData.lastName}{" "}
                    {!!memberData.memberNo && "#" + memberData.memberNo}
                  </li>
                )}
                <li>{getPriceModeDisplay(getMode(subscription))}</li>
              </ul>
            </div>
          </Col>
        </Row>
        <Row>
          <Col>
            <Form.Group className={"mb-2"}>
              {ALL_MODES.map((mode) => (
                <div
                  key={mode}
                  className={"d-flex flex-row gap-2 align-items-center"}
                >
                  <Form.Check
                    id={"mode_" + mode}
                    name={mode}
                    label={getPriceModeDisplay(mode)}
                    onChange={() => setPriceMode(mode)}
                    type={"radio"}
                    checked={priceMode === mode}
                    disabled={isBiddingRoundMode(mode)}
                  />
                  <TapirHelpButton buttonSize={"sm"} text={getHelpText(mode)} />
                </div>
              ))}
            </Form.Group>
            <p className="text-muted small mt-2 mb-0">
              Die Modi „Bietrunde: Gebot“ und „Bietrunde: Auto-Verlängert“
              werden durch die Bietrunde gesetzt und können hier nicht manuell
              gewählt werden.
            </p>
          </Col>
        </Row>
        {priceMode === "custom" && (
          <>
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
                    <Form.Control
                      value={customPrice}
                      onChange={(event) => {
                        setCustomPrice(event.target.value);
                        setError(undefined);
                      }}
                      placeholder={getPriceModeDisplay("custom")}
                      type={"number"}
                      min={0}
                      step={0.01}
                    />
                  </Form.Group>
                </Col>
              </Row>
            )}
          </>
        )}
      </>
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
          <Modal.Title>Vertragspreis personalisieren</Modal.Title>
        </span>
      </Modal.Header>

      <Modal.Body>{getBodyContent()}</Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Preis ändern"}
          loading={loading}
          disabled={isBiddingRoundMode(priceMode)}
          onClick={onConfirmChange}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default SubscriptionChangePriceModal;
