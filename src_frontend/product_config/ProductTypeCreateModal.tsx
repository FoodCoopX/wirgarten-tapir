import React, { useEffect, useState } from "react";
import { Col, Modal, Row, Spinner } from "react-bootstrap";
import {
  DeliveriesApi,
  DeliveryCycleEnum,
  GrowingPeriod,
  ProductsApi,
  ProductType,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import { getPeriodIdFromUrl } from "./get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import ProductTypeForm from "./ProductTypeForm.tsx";

interface ProductTypeCreateModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const ProductTypeCreateModal: React.FC<ProductTypeCreateModalProps> = ({
  show,
  onHide,
  csrfToken,
  setToastDatas,
}) => {
  const [loading, setLoading] = useState(true);
  const productsApi = useApi(ProductsApi, csrfToken);
  const deliveriesApi = useApi(DeliveriesApi, csrfToken);
  const [productTypesWithoutCapacity, setProductTypesWithoutCapacity] =
    useState<ProductType[]>([]);
  const [mode, setMode] = useState<"select" | "create">("select");
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
  const [saving, setSaving] = useState(false);
  const [selectedProductTypeId, setSelectedProductTypeId] = useState<
    string | undefined
  >();

  useEffect(() => {
    if (!getPeriodIdFromUrl() || !show) return;
    setLoading(true);

    productsApi
      .productsApiProductTypesWithoutCapacityRetrieve({
        growingPeriodId: getPeriodIdFromUrl(),
      })
      .then((result) => {
        setProductTypesWithoutCapacity(result.productTypesWithoutCapacity);
        setShowAssociationMembership(result.showAssociationMembership);
        setShowJokers(result.showJokers);
        setShowNoticePeriod(result.showNoticePeriod);
        setDeliveryCycleOptions(result.deliveryCycleOptions);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der ProduktTyp-Daten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));

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

    setMode("select");
  }, [show]);

  function switchToCreateMode(productType: ProductType | undefined) {
    setMode("create");
    setSelectedProductTypeId(undefined);
    if (!productType) return;

    setSelectedProductTypeId(productType.id!);
    setName(productType.name);
    setIconLink(productType.iconLink ?? "");
    setCapacity(0);
    setDeliveryCycle(productType.deliveryCycle ?? "weekly");
    setTaxRate(0.19);
    setTaxRateChangeDate(new Date());
    setSingleSubscriptionOnly(productType.singleSubscriptionOnly ?? false);
    setMustBeSubscribedTo(productType.mustBeSubscribedTo ?? false);
    setDescriptionBestellwizardShort(
      productType.descriptionBestellwizardShort ?? "",
    );
    setDescriptionBestellwizardLong(
      productType.descriptionBestellwizardLong ?? "",
    );
    setOrderInBestellwizard(productType.orderInBestellwizard ?? 1);
    setContractLink(productType.contractLink ?? "");
  }

  function onSave() {
    setSaving(true);

    productsApi
      .productsApiExtendedProductTypeCreate({
        saveExtendedProductTypeRequest: {
          productTypeId: selectedProductTypeId,
          growingPeriodId: getPeriodIdFromUrl(),
          extendedProductType: {
            isAssociationMembership: isAssociationMembership,
            contractLink: contractLink,
            orderInBestellwizard: orderInBestellwizard,
            descriptionBestellwizardLong: descriptionBestellwizardLong,
            descriptionBestellwizardShort: descriptionBestellwizardShort,
            mustBeSubscribedTo: mustBeSubscribedTo,
            singleSubscriptionOnly: singleSubscriptionOnly,
            taxRateChangeDate: taxRateChangeDate,
            taxRate: taxRate,
            noticePeriod: noticePeriod,
            isAffectedByJokers: isAffectedByJokers,
            deliveryCycle: deliveryCycle,
            capacity: capacity,
            iconLink: iconLink,
            name: name,
          },
        },
      })
      .then(() => location.reload())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsperiode",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function getModalBody() {
    if (loading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    if (mode === "select") {
      return (
        <Modal.Body>
          <Row>
            <Col>
              {productTypesWithoutCapacity.length > 0 && (
                <>
                  <p>
                    Folgende Produkttypen existieren schon aber sind noch nicht
                    mit dieser Vertragsperiode verbunden:
                  </p>
                  <ul>
                    {productTypesWithoutCapacity.map((type) => (
                      <li key={type.id}>
                        <span className={"d-flex flex-row gap-2"}>
                          {type.name}{" "}
                          <TapirButton
                            text={"Verbinden"}
                            size={"sm"}
                            icon={"add_link"}
                            variant={"outline-primary"}
                            onClick={() => switchToCreateMode(type)}
                          />
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div className={"d-flex flex-row gap-2 align-items-center"}>
                    <div>
                      Alternativ kannst du ein ganz neues Produkttyp erzeugen:
                    </div>
                    <TapirButton
                      text={"Neues Produkttyp erzeugen"}
                      icon={"add"}
                      variant={"outline-primary"}
                      size={"sm"}
                      onClick={() => switchToCreateMode(undefined)}
                    />
                  </div>
                </>
              )}
            </Col>
          </Row>
        </Modal.Body>
      );
    }

    if (growingPeriod === undefined) {
      return <Modal.Body>Vertragsperiode fehlt</Modal.Body>;
    }

    return (
      <Modal.Body>
        <ProductTypeForm
          setContractLink={setContractLink}
          name={name}
          setName={setName}
          iconLink={iconLink}
          setIconLink={setIconLink}
          growingPeriod={growingPeriod}
          capacity={capacity}
          setCapacity={setCapacity}
          deliveryCycle={deliveryCycle}
          setDeliveryCycle={setDeliveryCycle}
          deliveryCycleOptions={deliveryCycleOptions}
          showJokers={showJokers}
          isAffectedByJokers={isAffectedByJokers}
          setIsAffectedByJokers={setIsAffectedByJokers}
          showNoticePeriod={showNoticePeriod}
          noticePeriod={noticePeriod}
          setNoticePeriod={setNoticePeriod}
          taxRate={taxRate}
          setTaxRate={setTaxRate}
          taxRateChangeDate={taxRateChangeDate}
          setTaxRateChangeDate={setTaxRateChangeDate}
          singleSubscriptionOnly={singleSubscriptionOnly}
          setSingleSubscriptionOnly={setSingleSubscriptionOnly}
          mustBeSubscribedTo={mustBeSubscribedTo}
          setMustBeSubscribedTo={setMustBeSubscribedTo}
          showAssociationMembership={showAssociationMembership}
          isAssociationMembership={isAssociationMembership}
          setIsAssociationMembership={setIsAssociationMembership}
          descriptionBestellwizardShort={descriptionBestellwizardShort}
          setDescriptionBestellwizardShort={setDescriptionBestellwizardShort}
          descriptionBestellwizardLong={descriptionBestellwizardLong}
          setDescriptionBestellwizardLong={setDescriptionBestellwizardLong}
          orderInBestellwizard={orderInBestellwizard}
          setOrderInBestellwizard={setOrderInBestellwizard}
          contractLink={contractLink}
        />
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"xl"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Produkt-Typ erzeugen</h5>
      </Modal.Header>
      {getModalBody()}
      {mode === "create" && (
        <Modal.Footer>
          <TapirButton
            text={"Speichern"}
            icon={"save"}
            variant={"primary"}
            loading={saving}
            onClick={onSave}
          />
        </Modal.Footer>
      )}
    </Modal>
  );
};

export default ProductTypeCreateModal;
