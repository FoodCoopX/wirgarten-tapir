import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import { CoopApi, Member, Subscription, SubscriptionsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
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

type PriceMode = "standard" | "custom" | "free";
const ALL_MODES: PriceMode[] = ["standard", "custom", "free"];

function getPriceModeDisplay(mode: PriceMode) {
  switch (mode) {
    case "standard":
      return "Standardbetrag";
    case "custom":
      return "Personalisierter Betrag";
    case "free":
      return "Beitragsbefreit";
  }
}

const SubscriptionChangePriceModal: React.FC<
  SubscriptionChangePriceModalProps
> = ({ onHide, show, subscriptionId, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<Subscription>();
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
        if (
          subscription.priceOverride === null ||
          subscription.priceOverride === undefined
        ) {
          setPriceMode("standard");
        } else if (Number.parseFloat(subscription.priceOverride) === 0) {
          setPriceMode("free");
        } else {
          setPriceMode("custom");
        }
      })
      .catch(
        async (error) =>
          await handleRequestError(
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

    coopApi.coopMembersRetrieve({ id: memberId }).then(setMemberData);
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
    }

    setLoading(true);

    subscriptionsApi
      .subscriptionsApiSubscriptionPriceOverrideCreate({
        subscriptionPriceOverrideChangeRequestRequest: {
          subscriptionId: subscriptionId,
          priceOverride: newPrice,
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
                <li>Produkt: {formatSubscription(subscription)}</li>
                <li>Start: {formatDateNumeric(subscription.startDate)}</li>
                <li>End: {formatDateNumeric(subscription.endDate)}</li>
                {memberData && (
                  <li>
                    Mitglied: {memberData.firstName} {memberData.lastName}{" "}
                    {!!memberData.memberNo && "#" + memberData.memberNo}
                  </li>
                )}
                <li>
                  {subscription.priceOverride
                    ? "Preis personalisiert: " +
                      formatCurrency(
                        Number.parseFloat(subscription.priceOverride),
                      )
                    : "Preis standard"}
                </li>
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
                  />
                  <TapirHelpButton
                    buttonSize={"sm"}
                    text={"WIP Hilfstext für " + getPriceModeDisplay(mode)}
                  />
                </div>
              ))}
            </Form.Group>
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
                      placeholder={"Kein personalisierter Preis"}
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
          onClick={onConfirmChange}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default SubscriptionChangePriceModal;
