import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import { CoopApi, Member, Subscription, SubscriptionsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
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
  const [currentPrice, setCurrentPrice] = useState("");

  useEffect(() => {
    if (!show) {
      return;
    }

    subscriptionsApi
      .subscriptionsSubscriptionsRetrieve({ id: subscriptionId })
      .then((subscription) => {
        setSubscription(subscription);
        setMemberId(subscription.member);
        setCurrentPrice(
          subscription.priceOverride
            ? subscription.priceOverride.toString()
            : "",
        );
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

    if (currentPrice !== "" && Number.isNaN(Number.parseFloat(currentPrice))) {
      setError("Ungültiger Zahl");
      return;
    }

    setLoading(true);

    subscriptionsApi
      .subscriptionsApiSubscriptionPriceOverrideCreate({
        subscriptionPriceOverrideChangeRequestRequest: {
          subscriptionId: subscriptionId,
          priceOverride: Number.parseFloat(currentPrice),
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
                  value={currentPrice}
                  onChange={(event) => {
                    setCurrentPrice(event.target.value);
                    setError(undefined);
                  }}
                  placeholder={"Kein personalisierter Preis"}
                  type={"number"}
                  min={0}
                  step={0.01}
                />
                <Form.Text>
                  Leer lassen um den Standardpreis zu verwenden.
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
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
