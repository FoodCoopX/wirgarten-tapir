import dayjs from "dayjs";
import React, { useEffect, useState } from "react";
import { Alert, Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import {
  CoopApi,
  DeliveriesApi,
  GrowingPeriod,
  Mpl,
  PaymentsApi,
  PickupLocation,
  PickupLocationsApi,
  Product,
  PublicProductType,
  Subscription,
  SubscriptionsApi
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

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
  const pickupApi = useApi(PickupLocationsApi, csrfToken);
  const paymentsApi = useApi(PaymentsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<Subscription>();
  const [memberName, setMemberName] = useState<string>();
  const [currentPaymentRhythm, setCurrentPaymentRhythm] = useState<
    string | undefined
  >();
  const [allowedPaymentRhythms, setAllowedPaymentRhythms] = useState<{
    [key: string]: string;
  }>({ "": "" });
  const [productTypesList, setProductTypesList] = useState<PublicProductType[]>(
    [],
  );
  const [productList, setProductList] = useState<Product[]>([]);
  const [growingPeriodList, setGrowingPeriodList] = useState<GrowingPeriod[]>(
    [],
  );
  const [pickupLocationsList, setPickupLocationsList] = useState<
    PickupLocation[]
  >([]);
  const [memberPickupLocation, setMemberPickupLocation] = useState<Mpl>();
  const [period, setPeriod] = useState<GrowingPeriod>();
  const [productType, setProductType] = useState<PublicProductType>();
  const [product, setProduct] = useState<Product>();
  const [startDate, setStartDate] = useState<Date>(new Date());
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [pickupLocation, setPickupLocation] = useState<PickupLocation>();
  const [paymentRhythm, setPaymentRhythm] = useState<string>();
  const [error, setError] = useState<string>();

  // TODO add Create Contract API Call

  useEffect(() => {
    if (!show) return;

    setLoading(true);

    Promise.all([
      coopApi.coopMembersRetrieve({ id: memberId }),
      subscriptionsApi.subscriptionsProductsList(),
      subscriptionsApi.subscriptionsPublicProductTypesList(),
      deliveriesApi.deliveriesGrowingPeriodsList(),
      pickupApi.pickupLocationsPickupLocationsList(),
      pickupApi.pickupLocationsApiGetMemberPickupLocationRetrieve({ memberId }),
      paymentsApi.paymentsApiMemberPaymentRhythmDataRetrieve({ memberId }),
    ])
      .then(
        ([
          Member,
          ProductsList,
          ProductTypesList,
          GrowingPeriodList,
          PickupLocationsList,
          MemberPickupLocation,
          PaymentRhythmData,
        ]) => {
          setMemberName(`${Member.firstName} ${Member.lastName}`);
          setProductList(ProductsList);
          setProductTypesList(ProductTypesList);
          setGrowingPeriodList(GrowingPeriodList);
          setPickupLocationsList(PickupLocationsList);
          setMemberPickupLocation(MemberPickupLocation);
          setCurrentPaymentRhythm(PaymentRhythmData.currentRhythm);
          setAllowedPaymentRhythms(PaymentRhythmData.allowedRhythms);
        },
      )
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Daten", setToastDatas),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function getBodyContent() {
    if (loading) {
      return <Spinner />;
    }
    if (memberName === undefined) {
      return <p>Fehler beim Laden der Mitgliedsdaten</p>;
    }
    return (
      <>
        <Row>
          <Form.Group>
            <Form.Label>Vertragsperiode</Form.Label>
            <Form.Select
              onChange={(event) => {
                setPeriod(growingPeriodList[parseInt(event.target.value)]);
              }}
            >
              {growingPeriodList.map((growingPeriod, index) => (
                <option key={growingPeriod.id} value={index}>
                  {`${formatDateNumeric(growingPeriod.startDate)} -
                    ${formatDateNumeric(growingPeriod.endDate)}`}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
        </Row>
        <Row>
          <Col>
            <Form.Group id={"start_date"}>
              <Form.Label>Start-Datum</Form.Label>
              <Form.Control
                type={"date"}
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
                onChange={(event) => {
                  const selectedDate = new Date(event.target.value);
                  if (dayjs(selectedDate).format("d") == "0") {
                    setEndDate(selectedDate);
                  } else if (new Date(selectedDate) === period?.endDate) {
                    setEndDate(selectedDate);
                  } else {
                    alert(
                      "Das End-Datum darf nur an einem Sonntag oder am letzten Tag der Periode sein.",
                    );
                  }
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
              Das End-Datum darf nur an einem Sonntag oder am letzten Tag der
              Periode sein.
            </p>
          </Col>
        </Row>
        <Row>
          <Col>
            <Form.Group>
              <Form.Label>Produkttyp</Form.Label>
              <Form.Select
                onChange={(event) =>
                  setProductType(productTypesList[parseInt(event.target.value)])
                }
              >
                {productTypesList.map((Product, index) => (
                  <option key={Product.id} value={index}>
                    {Product.name}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </Col>
          <Col>
            <Form.Group>
              <Form.Label>Produkt</Form.Label>
              <Form.Select
                onChange={(event) => {
                  setProduct(
                    productList.find((product) => {
                      return product.id === event.target.value;
                    }),
                  );
                }}
              >
                {productList
                  .filter((Product) => {
                    return productType
                      ? Product.type.id === productType.id
                      : Product.type.id === productTypesList[0].id;
                  })
                  .map((Product) => (
                    <option key={Product.name} value={Product.id}>
                      {Product.name}
                    </option>
                  ))}
              </Form.Select>
            </Form.Group>
          </Col>
        </Row>
        <Row>
          <Form.Group>
            <Form.Label>Abholort</Form.Label>
            <Form.Select
              onChange={(event) => {
                setPickupLocation(
                  pickupLocationsList[parseInt(event.target.value)],
                );
              }}
            >
              {pickupLocationsList
                .filter((pickupLocation) => {
                  return memberPickupLocation?.hasLocation
                    ? pickupLocation.id === memberPickupLocation.location?.id
                    : [];
                })
                .map((pickupLocation, index) => (
                  <option key={pickupLocation.id} value={index}>
                    {pickupLocation.name}
                  </option>
                ))}
            </Form.Select>
          </Form.Group>
        </Row>
        <Row>
          {Object.entries(allowedPaymentRhythms).length > 1 && (
            <Form.Group>
              <Form.Label>Zahlungsintervall </Form.Label>
              <Form.Select
                onChange={(event) => {
                  setPaymentRhythm(event.target.value);
                }}
              >
                {Object.entries(allowedPaymentRhythms)
                  .filter(([rhythm, name]) => {
                    return currentPaymentRhythm
                      ? currentPaymentRhythm === rhythm
                      : [];
                  })
                  .map(([rhythm, name]) => (
                    <option key={rhythm} value={rhythm}>
                      {name}
                    </option>
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
            {memberName && <h4>Neuer Vertrag für {memberName}</h4>}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>{getBodyContent()}</Modal.Body>
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
