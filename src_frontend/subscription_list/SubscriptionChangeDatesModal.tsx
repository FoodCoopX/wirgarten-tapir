import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import { ToastData } from "../types/ToastData.ts";
import { useApi } from "../hooks/useApi.ts";
import { CoopApi, Member, Subscription, SubscriptionsApi } from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";
import formatSubscription from "../utils/formatSubscription.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import dayjs from "dayjs";
import TapirButton from "../components/TapirButton.tsx";

interface SubscriptionChangeDatesModalProps {
  onHide: () => void;
  show: boolean;
  subscriptionId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const SubscriptionChangeDatesModal: React.FC<
  SubscriptionChangeDatesModalProps
> = ({ onHide, show, subscriptionId, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<Subscription>();
  const [memberId, setMemberId] = useState<string>();
  const [memberData, setMemberData] = useState<Member>();
  const [startDate, setStartDate] = useState<Date>();
  const [endDate, setEndDate] = useState<Date | null | undefined>();
  const [error, setError] = useState<string>();

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
      .finally(() => setLoading(false));

    setLoading(true);
  }, [show]);

  useEffect(() => {
    if (!show || !memberId) {
      return;
    }

    coopApi.coopMembersRetrieve({ id: memberId }).then(setMemberData);
  }, [memberId, show]);

  useEffect(() => {
    if (!subscription) {
      return;
    }

    setStartDate(subscription.startDate);
    setEndDate(subscription.endDate);
  }, [subscription]);

  function onConfirmChange() {
    if (!subscription || !startDate || !endDate) {
      return;
    }

    if (
      startDate === subscription.startDate &&
      endDate === subscription.endDate
    ) {
      alert("Die Daten sind nicht geändert worden.");
      return;
    }

    setLoading(true);

    subscriptionsApi
      .subscriptionsApiDatesChangeCreate({
        subscriptionDateChangeRequest: {
          subscriptionId: subscriptionId,
          startDate: startDate,
          endDate: endDate,
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
          "Fehler beim Laden der Verteilstationen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    setError(undefined);
  }, [startDate, endDate]);

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
                    {memberData.memberNo && "#" + memberData.memberNo}
                  </li>
                )}
              </ul>
            </div>
          </Col>
        </Row>
        {subscription && (
          <Row>
            <Col>
              {startDate && (
                <Form.Group>
                  <Form.Label>Start-Datum</Form.Label>
                  <Form.Control
                    type={"date"}
                    value={dayjs(startDate).format("YYYY-MM-DD")}
                    onChange={(event) => {
                      setStartDate(new Date(event.target.value));
                    }}
                  />
                </Form.Group>
              )}
            </Col>
            <Col>
              {endDate && (
                <Form.Group>
                  <Form.Label>End-Datum</Form.Label>
                  <Form.Control
                    type={"date"}
                    value={dayjs(endDate).format("YYYY-MM-DD")}
                    onChange={(event) => {
                      setEndDate(new Date(event.target.value));
                    }}
                  />
                </Form.Group>
              )}
            </Col>
          </Row>
        )}
        {error && (
          <Row className={"mt-4"}>
            <Col>
              <Alert variant={"danger"}>{error}</Alert>
            </Col>
          </Row>
        )}
        <Row className={"mt-2"}>
          <Col>
            <p>
              Das End-Datum darf nur am Tag der Kommissioniervariable gesetzt
              werden (sehe Konfig-Seite).
            </p>
            <p>
              Wenn das End-Datum nicht am Vertragsperiode-Ende gesetzt wird,
              wird der Vertrag als gekündigt markiert: es wird nicht mehr
              verlängert. Soll dieses Vertrag schon verlängert worden sein, wird
              die Verlängerung gelöscht.
            </p>
            <p>
              Die Zahlungsreihe für dieses Mitglied soll geprüft werden: es
              ergeben sich ggf. Rückzahlungen
            </p>
            <p>Das Mitglied wird kein automatisierte Mail bekommen.</p>
          </Col>
        </Row>
      </>
    );
  }

  return (
    <>
      <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
        <Modal.Header closeButton>
          <Modal.Title>
            <h4>Vertragsstart-anpassen/Sonderkündigung</h4>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>{getBodyContent()}</Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Daten ändern"}
            loading={loading}
            onClick={onConfirmChange}
          />
        </Modal.Footer>
      </Modal>
    </>
  );
};

export default SubscriptionChangeDatesModal;
