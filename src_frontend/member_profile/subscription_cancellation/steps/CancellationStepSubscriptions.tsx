import React, { Dispatch, SetStateAction } from "react";
import { Form, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import {
  ProductForCancellation,
  SolidarityContributionCancellationData,
} from "../../../api-client";
import TapirButton from "../../../components/TapirButton.tsx";
import { formatDateText } from "../../../utils/formatDateText.ts";
import TapirHelpButton from "../../../components/TapirHelpButton.tsx";
import { formatDateNumeric } from "../../../utils/formatDateNumeric.ts";
import { formatDateTextLong } from "../../../utils/formatDateTextLong.ts";

interface CancellationStepSubscriptionsProps {
  errors: string[];
  subscribedProducts: ProductForCancellation[];
  selectedProducts: ProductForCancellation[];
  setSelectedProducts: Dispatch<SetStateAction<ProductForCancellation[]>>;
  canCancelCoopMembership: boolean;
  membershipText: string;
  cancelCoopMembershipSelected: boolean;
  setCancelCoopMembershipSelected: Dispatch<SetStateAction<boolean>>;
  goToNextStep: () => void;
  solidarityContributionData?: SolidarityContributionCancellationData;
  cancelSolidarityContribution: boolean;
  setCancelSolidarityContribution: (cancel: boolean) => void;
  trialPeriodIsFlexible: boolean;
}

function getCheckboxLabelProduct(subscribedProduct: ProductForCancellation) {
  let result =
    subscribedProduct.product.type.name +
    " (" +
    subscribedProduct.product.name +
    ") zum " +
    formatDateText(subscribedProduct.cancellationDate) +
    " kündigen";
  if (subscribedProduct.isInTrial) {
    result += " (Probezeit)";
  }
  result += ".";
  return result;
}

function getCheckboxLabelSolidarityContribution(
  data: SolidarityContributionCancellationData,
) {
  let result =
    "Solidarbeitrag zum " + formatDateText(data.cancellationDate) + " kündigen";

  if (data.isInTrial) {
    result += " (Probezeit)";
  }
  result += ".";

  return result;
}

function buildNoticePeriodText(subscribedProduct: ProductForCancellation) {
  let unit;
  if (subscribedProduct.noticePeriodUnit === "months") {
    unit = subscribedProduct.noticePeriodDuration <= 1 ? "Monat" : "Monate";
  } else {
    unit = subscribedProduct.noticePeriodDuration <= 1 ? "Woche" : "Wochen";
  }
  return (
    <p>
      Beachte: Nach Ablauf der Probezeit kannst du erst wieder unter
      Berücksichtigung der regulären Kündigungsfrist (
      {subscribedProduct.noticePeriodDuration} {unit}) zum{" "}
      {formatDateNumeric(subscribedProduct.subscriptionEndDate)} kündigen.
    </p>
  );
}

function buildHelpText(
  subscribedProduct: ProductForCancellation,
  trialPeriodIsFlexible: boolean,
) {
  if (!subscribedProduct.isInTrial) {
    return (
      <p>
        Du kannst deinen Vertrag bis zum{" "}
        {formatDateNumeric(subscribedProduct.lastDayOfNoticePeriod)} zum{" "}
        {formatDateNumeric(subscribedProduct.cancellationDate)} kündigen. Nach
        Ablauf der Kündigungsfrist verlängert sich dein Vertrag automatisch um
        ein weiteres Jahr.
      </p>
    );
  }

  if (trialPeriodIsFlexible) {
    return (
      <>
        <p>
          Du kannst deinen Vertrag bis zum{" "}
          {formatDateTextLong(subscribedProduct.dateLimitForTrialCancellation)}{" "}
          um 23.59 Uhr kündigen, damit dein Vertrag am{" "}
          {formatDateTextLong(subscribedProduct.cancellationDate)} beendet wird.
          Wenn du deine komplette Probezeit nutzen willst, dann kündige in der
          letzten Lieferwoche bis zum{" "}
          {subscribedProduct.dateLimitForTrialCancellation
            ? subscribedProduct.dateLimitForTrialCancellation.toLocaleDateString(
                "de-DE",
                { weekday: "long" },
              )
            : "Kein Datum"}{" "}
          um 23.59 Uhr.
        </p>

        {buildNoticePeriodText(subscribedProduct)}
      </>
    );
  }

  return (
    <>
      <p>
        Du kannst deinen Vertrag bis zum{" "}
        {formatDateTextLong(subscribedProduct.dateLimitForTrialCancellation)} um
        23.59 Uhr kündigen, damit dein Vertrag am{" "}
        {formatDateTextLong(subscribedProduct.cancellationDate)} beendet wird.
      </p>

      {buildNoticePeriodText(subscribedProduct)}
    </>
  );
}

const CancellationStepSubscriptions: React.FC<
  CancellationStepSubscriptionsProps
> = ({
  errors,
  subscribedProducts,
  selectedProducts,
  setSelectedProducts,
  canCancelCoopMembership,
  membershipText,
  cancelCoopMembershipSelected,
  setCancelCoopMembershipSelected,
  goToNextStep,
  solidarityContributionData,
  cancelSolidarityContribution,
  setCancelSolidarityContribution,
  trialPeriodIsFlexible,
}) => {
  function changeSelection(product: ProductForCancellation, selected: boolean) {
    if (selected && !selectedProducts.includes(product)) {
      setSelectedProducts([...selectedProducts, product]);
    } else if (!selected && selectedProducts.includes(product)) {
      setSelectedProducts(
        selectedProducts.filter((p: ProductForCancellation) => p !== product),
      );
    }
  }

  return (
    <>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"subscriptionCancellationModalForm"}
        >
          {errors.map((error, index) => (
            <div className={"text-danger"} key={index}>
              {error}
            </div>
          ))}

          <div>Welche Verträge möchtest du kündigen?</div>

          <Form.Text>
            Wenn du früher kündigen möchtest, wende dich bitte an unsere
            Verwaltung.
          </Form.Text>

          {subscribedProducts.map(
            (subscribedProduct: ProductForCancellation) => {
              return (
                <Form.Group
                  key={subscribedProduct.product.id}
                  controlId={subscribedProduct.product.id}
                  className={"d-flex flex-row gap-2 align-items-center"}
                >
                  <Form.Check
                    onChange={(event) =>
                      changeSelection(subscribedProduct, event.target.checked)
                    }
                    required={false}
                    checked={selectedProducts.includes(subscribedProduct)}
                    label={getCheckboxLabelProduct(subscribedProduct)}
                    className={"mb-0"}
                  />
                  <TapirHelpButton
                    text={buildHelpText(
                      subscribedProduct,
                      trialPeriodIsFlexible,
                    )}
                    buttonSize={"sm"}
                  />
                </Form.Group>
              );
            },
          )}
          {solidarityContributionData?._exists && (
            <Form.Group controlId="cancelSolidarityContribution">
              <Form.Check
                onChange={(event) =>
                  setCancelSolidarityContribution(event.target.checked)
                }
                required={false}
                checked={cancelSolidarityContribution}
                label={getCheckboxLabelSolidarityContribution(
                  solidarityContributionData,
                )}
              />
            </Form.Group>
          )}
          {canCancelCoopMembership && (
            <Form.Group controlId="cancelCoopMembership">
              <Form.Check
                onChange={(event) =>
                  setCancelCoopMembershipSelected(event.target.checked)
                }
                required={false}
                checked={cancelCoopMembershipSelected}
                label={membershipText + " widerrufen"}
              />
            </Form.Group>
          )}
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"outline-danger"}
          icon={"contract_delete"}
          text={"Weiter"}
          onClick={goToNextStep}
          disabled={
            !cancelCoopMembershipSelected &&
            !cancelSolidarityContribution &&
            selectedProducts.length === 0
          }
        />
      </Modal.Footer>
    </>
  );
};

export default CancellationStepSubscriptions;
