import React, { useEffect, useState } from "react";
import { Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import {
  DeliveriesApi,
  DeliveryCycleEnum,
  GrowingPeriod,
  ProductsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import {
  getPeriodIdFromUrl,
  getProductTypeIdFromUrl,
} from "./get_parameter_from_url.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";
import dayjs from "dayjs";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface ProductTypeModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const ProductTypeModal: React.FC<ProductTypeModalProps> = ({
  show,
  onHide,
  csrfToken,
  setToastDatas,
}) => {
  const productsApi = useApi(ProductsApi, csrfToken);
  const deliveriesApi = useApi(DeliveriesApi, csrfToken);
  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showJokers, setShowJokers] = useState(false);
  const [showAssociationMembership, setShowAssociationMembership] =
    useState(false);
  const [showNoticePeriod, setShowNoticePeriod] = useState(false);
  const [name, setName] = useState("");
  const [descriptionBestellwizardShort, setDescriptionBestellwizardShort] =
    useState("");
  const [descriptionBestellwizardLong, setDescriptionBestellwizardLong] =
    useState("");
  const [orderInBestellwizard, setOrderInBestellwizard] = useState(0);
  const [iconLink, setIconLink] = useState("");
  const [contractLink, setContractLink] = useState("");
  const [capacity, setCapacity] = useState(0);
  const [deliveryCycle, setDeliveryCycle] = useState<DeliveryCycleEnum>(
    DeliveryCycleEnum.NoDelivery,
  );
  const [deliveryCycleOptions, setDeliveryCycleOptions] = useState<{
    [key: string]: string;
  }>({});
  const [noticePeriod, setNoticePeriod] = useState<number | undefined>(0);
  const [taxRate, setTaxRate] = useState(0);
  const [taxRateChangeDate, setTaxRateChangeDate] = useState(new Date());
  const [singleSubscriptionOnly, setSingleSubscriptionOnly] = useState(false);
  const [isAffectedByJokers, setIsAffectedByJokers] = useState(false);
  const [mustBeSubscribedTo, setMustBeSubscribedTo] = useState(false);
  const [isAssociationMembership, setIsAssociationMembership] = useState(false);
  const [growingPeriod, setGrowingPeriod] = useState<GrowingPeriod>();

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);

    if (!getProductTypeIdFromUrl()) return;
    if (!getPeriodIdFromUrl()) return;

    productsApi
      .productsApiExtendedProductTypeRetrieve({
        productTypeId: getProductTypeIdFromUrl(),
        growingPeriodId: getPeriodIdFromUrl(),
      })
      .then((result) => {
        setShowJokers(result.showJokers);
        setShowAssociationMembership(result.showAssociationMembership);
        setShowNoticePeriod(result.showNoticePeriod);
        setDeliveryCycleOptions(result.deliveryCycleOptions);
        setName(result.extendedProductType.name);
        setDescriptionBestellwizardLong(
          result.extendedProductType.descriptionBestellwizardLong ?? "",
        );
        setDescriptionBestellwizardShort(
          result.extendedProductType.descriptionBestellwizardShort ?? "",
        );
        setOrderInBestellwizard(
          result.extendedProductType.orderInBestellwizard,
        );
        setIconLink(result.extendedProductType.iconLink ?? "");
        setContractLink(result.extendedProductType.contractLink ?? "");
        setCapacity(result.extendedProductType.capacity);
        setDeliveryCycle(result.extendedProductType.deliveryCycle);
        setNoticePeriod(result.extendedProductType.noticePeriod);
        setTaxRate(result.extendedProductType.taxRate);
        setTaxRateChangeDate(result.extendedProductType.taxRateChangeDate);
        setSingleSubscriptionOnly(
          result.extendedProductType.singleSubscriptionOnly,
        );
        setIsAffectedByJokers(result.extendedProductType.isAffectedByJokers);
        setMustBeSubscribedTo(result.extendedProductType.mustBeSubscribedTo);
        setIsAssociationMembership(
          result.extendedProductType.isAssociationMembership,
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der ProduktTyp-Daten",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));

    deliveriesApi
      .deliveriesGrowingPeriodsRetrieve({ id: getPeriodIdFromUrl() })
      .then(setGrowingPeriod)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsperiode",
          setToastDatas,
        ),
      );
  }, [show]);

  function onSave() {
    setSaving(true);

    productsApi
      .productsApiExtendedProductTypePartialUpdate({
        patchedSaveExtendedProductTypeRequest: {
          productTypeId: getProductTypeIdFromUrl(),
          growingPeriodId: getPeriodIdFromUrl(),
          extendedProductType: {
            name: name,
            iconLink: iconLink,
            capacity: capacity,
            deliveryCycle: deliveryCycle,
            isAffectedByJokers: isAffectedByJokers,
            noticePeriod: noticePeriod,
            taxRate: taxRate,
            taxRateChangeDate: taxRateChangeDate,
            singleSubscriptionOnly: singleSubscriptionOnly,
            mustBeSubscribedTo: mustBeSubscribedTo,
            isAssociationMembership: isAssociationMembership,
            descriptionBestellwizardShort: descriptionBestellwizardShort,
            descriptionBestellwizardLong: descriptionBestellwizardLong,
            orderInBestellwizard: orderInBestellwizard,
            contractLink: contractLink,
          },
        },
      })
      .then(() => location.reload())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Produkt-Typ",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <Modal.Body>
        <Row>
          <Col>
            <Row>
              <h5>Allgemein</h5>
            </Row>
            <Row>
              <Form.Group controlId={"name"}>
                <Form.Label>Name</Form.Label>
                <Form.Control
                  type={"text"}
                  placeholder={"Name"}
                  onChange={(event) => setName(event.target.value)}
                  required={true}
                  value={name}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"iconLink"}>
                <Form.Label>Icon Link</Form.Label>
                <Form.Control
                  type={"text"}
                  placeholder={"Icon Link"}
                  onChange={(event) => setIconLink(event.target.value)}
                  required={true}
                  value={iconLink}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"capacity"}>
                <Form.Label>
                  Produkt Kapazität in Produkt-Größe für die Vertragsperiode{" "}
                  {formatDateNumeric(growingPeriod?.startDate)} bis{" "}
                  {formatDateNumeric(growingPeriod?.endDate)}
                </Form.Label>
                <Form.Control
                  type={"number"}
                  onChange={(event) =>
                    setCapacity(parseFloat(event.target.value))
                  }
                  required={true}
                  value={capacity}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"delivery_cycle"}>
                <Form.Label>Liefer-/Abholzyklus</Form.Label>
                <Form.Select
                  onChange={(event) =>
                    setDeliveryCycle(event.target.value as DeliveryCycleEnum)
                  }
                  required={true}
                  value={deliveryCycle}
                >
                  {Object.entries(deliveryCycleOptions).map(([key, value]) => {
                    return (
                      <option key={key} value={key}>
                        {value}
                      </option>
                    );
                  })}
                </Form.Select>
              </Form.Group>
            </Row>
            {showJokers && (
              <Row className={"mt-2"}>
                <Form.Group controlId={"is_affected_by_jokers"}>
                  <Form.Check
                    onChange={(event) =>
                      setIsAffectedByJokers(event.target.checked)
                    }
                    required={false}
                    checked={isAffectedByJokers}
                    label={"Nimmt am Joker-Verfahren teil"}
                  />
                </Form.Group>
              </Row>
            )}
          </Col>
          <Col>
            <Row>
              <h5>Verträge</h5>
            </Row>
            {showNoticePeriod && (
              <Row>
                <Form.Group controlId={"notice_period"}>
                  <Form.Label>Kündigungsfrist</Form.Label>
                  <Form.Control
                    type={"number"}
                    onChange={(event) =>
                      setNoticePeriod(parseInt(event.target.value))
                    }
                    required={true}
                    value={noticePeriod}
                  />
                  <Form.Text>Anzahl an Monate</Form.Text>
                </Form.Group>
              </Row>
            )}
            <Row className={"mt-2"}>
              <Form.Group controlId={"tax_rate"}>
                <Form.Label>Mehrwertsteuersatz</Form.Label>
                <Form.Control
                  type={"number"}
                  onChange={(event) =>
                    setTaxRate(parseFloat(event.target.value))
                  }
                  required={true}
                  value={taxRate}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"tax_rate_change_date"}>
                <Form.Label>Neuer Mehrwertsteuersatz gültig ab</Form.Label>
                <Form.Control
                  type={"date"}
                  onChange={(event) =>
                    setTaxRateChangeDate(new Date(event.target.value))
                  }
                  required={true}
                  value={dayjs(taxRateChangeDate).format("YYYY-MM-DD")}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"single_subscription_only"}>
                <Form.Check
                  onChange={(event) =>
                    setSingleSubscriptionOnly(event.target.checked)
                  }
                  required={false}
                  checked={singleSubscriptionOnly}
                  label={"Nur Einzelabonnement möglich"}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"must_be_subscribed_to"}>
                <Form.Check
                  onChange={(event) =>
                    setMustBeSubscribedTo(event.target.checked)
                  }
                  required={false}
                  checked={mustBeSubscribedTo}
                  label={"Ist Pflicht"}
                />
              </Form.Group>
            </Row>
            {showAssociationMembership && (
              <Row className={"mt-2"}>
                <Form.Group controlId={"is_association_membership"}>
                  <Form.Check
                    onChange={(event) =>
                      setIsAssociationMembership(event.target.checked)
                    }
                    required={false}
                    checked={isAssociationMembership}
                    label={"Ist Pflicht"}
                  />
                </Form.Group>
              </Row>
            )}
          </Col>
          <Col>
            <h5>BestellWizard</h5>
            <Row>
              <Form.Group controlId={"description_bestellwizard_short"}>
                <Form.Label>
                  Beschreibung im Bestellwizard bei der erste Seite (Produkt-Typ
                  Auswahl)
                </Form.Label>
                <Form.Control
                  type={"text"}
                  onChange={(event) =>
                    setDescriptionBestellwizardShort(event.target.value)
                  }
                  required={true}
                  value={descriptionBestellwizardShort}
                  as={"textarea"}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"description_bestellwizard_long"}>
                <Form.Label>
                  Beschreibung im Bestellwizard bei der Produkt-Spezifische
                  Seite
                </Form.Label>
                <Form.Control
                  type={"text"}
                  onChange={(event) =>
                    setDescriptionBestellwizardLong(event.target.value)
                  }
                  required={true}
                  value={descriptionBestellwizardLong}
                  as={"textarea"}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"order_in_bestellwizard"}>
                <Form.Label>
                  Reihenfolge im BestellWizard (kleiner ist früher)
                </Form.Label>
                <Form.Control
                  type={"number"}
                  onChange={(event) =>
                    setOrderInBestellwizard(parseInt(event.target.value))
                  }
                  required={true}
                  value={orderInBestellwizard}
                  step={1}
                />
              </Form.Group>
            </Row>
            <Row className={"mt-2"}>
              <Form.Group controlId={"contract_link"}>
                <Form.Label>Link zu den Vertragsgrundsätzen</Form.Label>
                <Form.Control
                  type={"text"}
                  onChange={(event) => setContractLink(event.target.value)}
                  required={true}
                  value={contractLink}
                />
              </Form.Group>
            </Row>
          </Col>
        </Row>
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"xl"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Produkt-Typ verwalten</h5>
      </Modal.Header>
      {getModalBody()}
      <Modal.Footer>
        <TapirButton
          text={"Speichern"}
          icon={"save"}
          variant={"primary"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default ProductTypeModal;
