import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import { ToastData } from "../types/ToastData.ts";
import { useApi } from "../hooks/useApi.ts";
import {
  CoopApi,
  DeliveriesApi,
  GrowingPeriod,
  Member,
  PickupLocation,
  PickupLocationsApi,
  Product,
  Subscription,
  SubscriptionsApi
} from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";
import dayjs from "dayjs";
import TapirButton from "../components/TapirButton.tsx";

interface SubscriptionAddContractModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

// @ts-ignore
const SubscriptionAddButtonModal: React.FC<
  SubscriptionAddContractModalProps
> = ({ onHide, show, memberId, csrfToken, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const deliveriesApi = useApi(DeliveriesApi, csrfToken);
  const pickupApi = useApi(PickupLocationsApi, csrfToken)
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<Subscription>();
  const [memberData, setMemberData] = useState<Member>();
  const [productList, setProductList] = useState<Product[]>();
  const [periodList, setPeriodList] = useState<GrowingPeriod[]>();
  const [pickupLocationsList, setPickupLocationsList] = useState<PickupLocation[]>();
  const [period, setPeriod] = useState<GrowingPeriod>();
  const [product, setProduct] = useState<Product>();
  const [startDate, setStartDate] = useState<Date>();
  const [endDate, setEndDate] = useState<Date | null | undefined>();
  const [error, setError] = useState<string>();

  useEffect(() => {
      if (!show) return;

      setLoading(true);

      coopApi
        .coopMembersRetrieve({ id: memberId })
        .then((response) => {
          setMemberData(response)
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Laden der persönliche Daten",
            setToastDatas,
          ),
        )
        .finally(() => setLoading(false));
    }, [show]);

  useEffect(() => {
      if (!show) return;

      setLoading(true);

      subscriptionsApi
        .subscriptionsProductsList()
        .then((response) => {
          setProductList(response)
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Laden der Produktliste",
            setToastDatas,
          ),
        )
        .finally(() => setLoading(false));
    }, [show]);

  useEffect(() => {
      if (!show) return;

      setLoading(true);

      deliveriesApi
        .deliveriesGrowingPeriodsList()
        .then((response) => {
          setPeriodList(response)
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Laden der Produktliste",
            setToastDatas,
          ),
        )
        .finally(() => setLoading(false));
    }, [show]);

  useEffect(() => {
      if (!show) return;

      setLoading(true);

      pickupApi
        .pickupLocationsPickupLocationsList()
        .then((response) => {
          setPickupLocationsList(response)
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Laden der Produktliste",
            setToastDatas,
          ),
        )
        .finally(() => setLoading(false));
    }, [show]);


  useEffect(() => {
      if (!show) return;

      setLoading(true);

      pickupApi
        .pickupLocationsPickupLocationsList()
        .then((response) => {
          setPickupLocationsList(response)
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Laden der Produktliste",
            setToastDatas,
          ),
        )
        .finally(() => setLoading(false));
    }, [show]);


  function getBodyContent() {
    if (loading) {
      return <Spinner />;
    }
    if (memberData === undefined) {
      return <p>Fehler beim Laden der Mitgliedsdaten</p>;
    }
    return (
      <>
        <Row>
          {periodList && (
            <Form.Group>
              <Form.Label>Vertragsperiode</Form.Label>
              <Form.Select
                onChange={(event) => {
                  // @ts-ignore
                  setPeriod(periodList[event.target.value]);

                }}>
                // TODO: When selecting for the first time opt.id is undefined
                {periodList.map((opt, index) => (
                  <option key={opt.id} value={index}>{dayjs(opt.startDate).format("YYYY")}</option>
                ))}
              </Form.Select>
            </Form.Group>
          )}
        </Row>
        <Row>
          <Col>
            <Form.Group id={"start_date"}>
              <Form.Label>Start-Datum</Form.Label>
              <Form.Control
                type={"date"}
                value={dayjs(period?.startDate).format("YYYY-MM-DD")}
                onChange={(event) => {
                  setStartDate(new Date(event.target.value));
                }}
              />
            </Form.Group>
          </Col>
          <Col>
            <Form.Group>
              <Form.Label>End-Datum</Form.Label>
              <Form.Control
                type={"date"}
                value={dayjs(period?.endDate).format("YYYY-MM-DD")}
                onChange={(event) => {
                  setEndDate(new Date(event.target.value));
                }}
              />
            </Form.Group>
          </Col>
        </Row>
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
          </Col>
        </Row>
        <Row>
          {periodList && (
            <Form.Group>
              <Form.Label>Produkttyp</Form.Label>
              <Form.Select
                onChange={(event) => {
                  // @ts-ignore
                  setProduct(productList[event.target.value]);
                }}>
                // TODO: When selecting for the first time opt.id is undefined
                {productList?.map((opt, index) => (
                  <option key={opt.id} value={index}>{opt.name}</option>
                ))}
              </Form.Select>
            </Form.Group>
          )}
        </Row>
        <Row>
          {pickupLocationsList && (
            <Form.Group>
              <Form.Label>Abholort</Form.Label>
              <Form.Select
                onChange={(event) => {
                  // @ts-ignore
                  setProduct(pickupLocationsList[event.target.value]);
                }}>
                // TODO: When selecting for the first time opt.id is undefined
                {pickupLocationsList?.map((opt, index) => (
                  <option key={opt.id} value={index}>{opt.name}</option>
                ))}
              </Form.Select>
            </Form.Group>
          )}
        </Row>
      </>
    );
  }

  return (
    <>
      <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
        <Modal.Header closeButton>
          <Modal.Title>
            {memberData && (
              <h4>
                Neuer Vertrag für {memberData.firstName} {memberData.lastName}{", "} {memberData.city}
              </h4>
            )}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {getBodyContent()}
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Vertrag hinzufügen"}
            loading={loading}
          />
        </Modal.Footer>
      </Modal>
    </>
  );
};

export default SubscriptionAddButtonModal;
