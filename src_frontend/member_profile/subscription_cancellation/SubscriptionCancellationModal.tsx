import React, { useEffect, useState } from "react";
import { Modal, Spinner } from "react-bootstrap";
import {
  LegalStatusEnum,
  ProductForCancellation,
  SolidarityContributionCancellationData,
  SubscriptionsApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import "dayjs/locale/de";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ToastData } from "../../types/ToastData.ts";
import CancellationStepSubscriptions from "./steps/CancellationStepSubscriptions.tsx";
import CancellationStepReasons from "./steps/CancellationStepReasons.tsx";
import CancellationStepConfirmation from "./steps/CancellationStepConfirmation.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";

interface SubscriptionCancellationModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

type CancellationStep = "subscriptions" | "reasons" | "confirmation";

const SubscriptionCancellationModal: React.FC<
  SubscriptionCancellationModalProps
> = ({ onHide, show, memberId, csrfToken, setToastDatas }) => {
  const api = useApi(SubscriptionsApi, csrfToken);
  const [subscribedProducts, setSubscribedProducts] = useState<
    ProductForCancellation[]
  >([]);
  const [solidarityContributionData, setSolidarityContributionData] =
    useState<SolidarityContributionCancellationData>();
  const [cancelSolidarityContribution, setCancelSolidarityContribution] =
    useState(false);
  const [canCancelCoopMembership, setCanCancelCoopMembership] = useState(false);
  const [legalStatus, setLegalStatus] = useState<LegalStatusEnum>();
  const [loading, setLoading] = useState(true);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState<
    ProductForCancellation[]
  >([]);
  const [cancelCoopMembershipSelected, setCancelCoopMembershipSelected] =
    useState(false);
  const [confirmationLoading, setConfirmationLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [defaultCancellationReasons, setDefaultCancellationReasons] = useState<
    string[]
  >([]);
  const [currentStep, setCurrentStep] =
    useState<CancellationStep>("subscriptions");
  const [selectedCancellationReasons, setSelectedCancellationReasons] =
    useState<string[]>([]);
  const [customCancellationReason, setCustomCancellationReason] = useState<
    string | undefined
  >();
  const [trialPeriodDuration, setTrialPeriodDuration] = useState<number>();

  useEffect(() => {
    if (!show) {
      return;
    }

    setSelectedProducts([]);
    setErrors([]);
    setCurrentStep("subscriptions");

    setLoading(true);
    api
      .subscriptionsCancellationDataRetrieve({ memberId: memberId })
      .then((data) => {
        setSubscribedProducts(data.subscribedProducts);
        setCanCancelCoopMembership(data.canCancelCoopMembership);
        setLegalStatus(data.legalStatus);
        setDefaultCancellationReasons(data.defaultCancellationReasons);
        setSolidarityContributionData(data.solidarityContributionData);
        if (data.showTrialPeriodHelpText) {
          setTrialPeriodDuration(data.trialPeriodDuration);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Kündigungsdaten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function getMembershipText() {
    if (legalStatus === LegalStatusEnum.Association) {
      return "Beitrittserklärung zum Verein";
    }
    return "Beitrittserklärung zur Genossenschaft";
  }

  function onConfirm() {
    setConfirmationLoading(true);

    const productIds = selectedProducts.map(
      (productForCancellation) => productForCancellation.product.id!,
    );

    api
      .subscriptionsCancelSubscriptionsCreate({
        cancelSubscriptionsRequestRequest: {
          memberId: memberId,
          productIds: productIds,
          cancelCoopMembership: cancelCoopMembershipSelected,
          cancellationReasons: selectedCancellationReasons,
          customCancellationReason: customCancellationReason,
          cancelSolidarityContribution: cancelSolidarityContribution,
        },
      })
      .then((response) => {
        if (response.subscriptionsCancelled) {
          location.reload();
          setShowConfirmationModal(false);
          onHide();
        } else {
          setErrors(response.errors);
        }
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Kündigen", setToastDatas),
      )
      .finally(() => setConfirmationLoading(false));
  }

  return (
    <Modal
      onHide={onHide}
      show={show && !showConfirmationModal}
      centered={true}
      size={"lg"}
    >
      <Modal.Header closeButton>
        <span
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <Modal.Title>Verträge kündigen</Modal.Title>
          {trialPeriodDuration && (
            <TapirHelpButton
              text={
                "Um zu bestimmen wann die Probezeit endet, werden die " +
                trialPeriodDuration +
                " Wochen ab der Montag vor der erste Lieferung berechnet, nicht ab dem Vertragsstart-Datum."
              }
            />
          )}
        </span>
      </Modal.Header>
      {loading ? (
        <>
          <Modal.Body>
            <Spinner />
          </Modal.Body>
          <Modal.Footer />
        </>
      ) : (
        <>
          {currentStep === "subscriptions" && (
            <CancellationStepSubscriptions
              errors={errors}
              subscribedProducts={subscribedProducts}
              selectedProducts={selectedProducts}
              setSelectedProducts={setSelectedProducts}
              canCancelCoopMembership={canCancelCoopMembership}
              membershipText={getMembershipText()}
              cancelCoopMembershipSelected={cancelCoopMembershipSelected}
              setCancelCoopMembershipSelected={setCancelCoopMembershipSelected}
              goToNextStep={() => setCurrentStep("reasons")}
              solidarityContributionData={solidarityContributionData}
              cancelSolidarityContribution={cancelSolidarityContribution}
              setCancelSolidarityContribution={setCancelSolidarityContribution}
            />
          )}
          {currentStep === "reasons" && (
            <CancellationStepReasons
              goToNextStep={() => setCurrentStep("confirmation")}
              selectedCancellationReasons={selectedCancellationReasons}
              setSelectedCancellationReasons={setSelectedCancellationReasons}
              defaultCancellationReasons={defaultCancellationReasons}
              customCancellationReason={customCancellationReason}
              setCustomCancellationReason={setCustomCancellationReason}
              goToPreviousStep={() => setCurrentStep("subscriptions")}
            />
          )}
          {currentStep === "confirmation" && (
            <CancellationStepConfirmation
              selectedCancellationReasons={selectedCancellationReasons}
              selectedProducts={selectedProducts}
              onConfirm={onConfirm}
              cancelCoopMembershipSelected={cancelCoopMembershipSelected}
              membershipText={getMembershipText()}
              customCancellationReasons={customCancellationReason}
              goToPreviousStep={() => setCurrentStep("reasons")}
              confirmationLoading={confirmationLoading}
            />
          )}
        </>
      )}
    </Modal>
  );
};

export default SubscriptionCancellationModal;
