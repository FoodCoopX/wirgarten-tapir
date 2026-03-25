import React, { useEffect, useState } from "react";
import { Modal, Spinner } from "react-bootstrap";
import {
  DeliveriesApi,
  DeliveryCycleEnum,
  GrowingPeriod,
  NoticePeriodUnitEnum,
  ProductsApi,
  type ProductTypeAccordionInBestellWizard,
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
import { CustomCycleDeliveryWeeks } from "../types/CustomCycleDeliveryWeeks.ts";

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
  const [canUpdateNoticePeriod, setCanUpdateNoticePeriod] = useState(false);
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
  const [customNoticePeriodEnabled, setCustomNoticePeriodEnabled] =
    useState<boolean>(false);
  const [noticePeriodDuration, setNoticePeriodDuration] = useState<number>(2);
  const [noticePeriodUnit, setNoticePeriodUnit] =
    useState<NoticePeriodUnitEnum>(NoticePeriodUnitEnum.Months);
  const [taxRate, setTaxRate] = useState(0);
  const [taxRateChangeDate, setTaxRateChangeDate] = useState(new Date());
  const [singleSubscriptionOnly, setSingleSubscriptionOnly] = useState(false);
  const [isAffectedByJokers, setIsAffectedByJokers] = useState(false);
  const [mustBeSubscribedTo, setMustBeSubscribedTo] = useState(false);
  const [isAssociationMembership, setIsAssociationMembership] = useState(false);
  const [forceWaitingList, setForceWaitingList] = useState(false);
  const [growingPeriod, setGrowingPeriod] = useState<GrowingPeriod>();
  const [accordions, setAccordions] = useState<
    ProductTypeAccordionInBestellWizard[]
  >([]);
  const [
    titleBestellWizardProductChoices,
    setTitleBestellWizardProductChoices,
  ] = useState("");
  const [titleBestellWizardIntro, setTitleBestellWizardIntro] = useState("");
  const [backgroundImageInBestellWizard, setBackgroundImageInBestellWizard] =
    useState("");
  const [deliveryWeeks, setDeliveryWeeks] = useState<CustomCycleDeliveryWeeks>(
    {},
  );
  const [allGrowingPeriods, setAllGrowingPeriods] = useState<GrowingPeriod[]>(
    [],
  );

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
        setCanUpdateNoticePeriod(result.canUpdateNoticePeriod);
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
        setCustomNoticePeriodEnabled(
          result.extendedProductType.noticePeriodDuration !== undefined,
        );
        setNoticePeriodDuration(
          result.extendedProductType.noticePeriodDuration ?? 2,
        );
        setNoticePeriodUnit(
          result.extendedProductType.noticePeriodUnit ??
            NoticePeriodUnitEnum.Months,
        );
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
        setForceWaitingList(result.extendedProductType.forceWaitingList);
        setAccordions(result.extendedProductType.accordionsInBestellWizard);
        setTitleBestellWizardProductChoices(
          result.extendedProductType.titleBestellwizardProductChoice,
        );
        setTitleBestellWizardIntro(
          result.extendedProductType.titleBestellwizardIntro,
        );
        setBackgroundImageInBestellWizard(
          result.extendedProductType.backgroundImageInBestellwizard,
        );
        setDeliveryWeeks(result.extendedProductType.customCycleDeliveryWeeks);
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

    deliveriesApi
      .deliveriesGrowingPeriodsList()
      .then(setAllGrowingPeriods)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsperioden",
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
            noticePeriodDuration: customNoticePeriodEnabled
              ? noticePeriodDuration
              : undefined,
            noticePeriodUnit: customNoticePeriodEnabled
              ? noticePeriodUnit
              : undefined,
            taxRate: taxRate,
            taxRateChangeDate: taxRateChangeDate,
            singleSubscriptionOnly: singleSubscriptionOnly,
            mustBeSubscribedTo: mustBeSubscribedTo,
            isAssociationMembership: isAssociationMembership,
            descriptionBestellwizardShort: descriptionBestellwizardShort,
            descriptionBestellwizardLong: descriptionBestellwizardLong,
            orderInBestellwizard: orderInBestellwizard,
            contractLink: contractLink,
            forceWaitingList: forceWaitingList,
            accordionsInBestellWizard: accordions,
            titleBestellwizardProductChoice: titleBestellWizardProductChoices,
            titleBestellwizardIntro: titleBestellWizardIntro,
            backgroundImageInBestellwizard: backgroundImageInBestellWizard,
            customCycleDeliveryWeeks: deliveryWeeks,
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
          globalSelectedGrowingPeriod={growingPeriod}
          capacity={capacity}
          setCapacity={setCapacity}
          deliveryCycle={deliveryCycle}
          setDeliveryCycle={setDeliveryCycle}
          deliveryCycleOptions={deliveryCycleOptions}
          showJokers={showJokers}
          isAffectedByJokers={isAffectedByJokers}
          setIsAffectedByJokers={setIsAffectedByJokers}
          showNoticePeriod={showNoticePeriod}
          canUpdateNoticePeriod={canUpdateNoticePeriod}
          noticePeriodDuration={noticePeriodDuration}
          setNoticePeriodDuration={setNoticePeriodDuration}
          noticePeriodEnabled={customNoticePeriodEnabled}
          setNoticePeriodEnabled={setCustomNoticePeriodEnabled}
          noticePeriodUnit={noticePeriodUnit}
          setNoticePeriodUnit={setNoticePeriodUnit}
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
          forceWaitingList={forceWaitingList}
          setForceWaitingList={setForceWaitingList}
          accordions={accordions}
          setAccordions={setAccordions}
          titleBestellWizardProductChoices={titleBestellWizardProductChoices}
          setTitleBestellWizardProductChoices={
            setTitleBestellWizardProductChoices
          }
          titleBestellWizardIntro={titleBestellWizardIntro}
          setTitleBestellWizardIntro={setTitleBestellWizardIntro}
          backgroundImageInBestellWizard={backgroundImageInBestellWizard}
          setBackgroundImageInBestellWizard={setBackgroundImageInBestellWizard}
          deliveryWeeks={deliveryWeeks}
          setDeliveryWeeks={setDeliveryWeeks}
          allGrowingPeriods={allGrowingPeriods}
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
