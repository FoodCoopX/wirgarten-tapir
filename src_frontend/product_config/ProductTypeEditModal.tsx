import React, { useEffect, useState } from "react";
import { Modal, Spinner } from "react-bootstrap";
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
import ProductTypeForm from "./ProductTypeForm.tsx";

interface ProductTypeEditModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const ProductTypeEditModal: React.FC<ProductTypeEditModalProps> = ({
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
    if (dataLoading || growingPeriod === undefined) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
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
        <h5 className={"mb-0"}>Produkt-Typ bearbeiten</h5>
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

export default ProductTypeEditModal;
