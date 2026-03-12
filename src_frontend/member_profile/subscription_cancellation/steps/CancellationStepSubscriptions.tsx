import React, { Dispatch, SetStateAction } from "react";
import { Form, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import {
  ProductForCancellation,
  SolidarityContributionCancellationData,
} from "../../../api-client";
import TapirButton from "../../../components/TapirButton.tsx";
import { formatDateText } from "../../../utils/formatDateText.ts";

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
                >
                  <Form.Check
                    onChange={(event) =>
                      changeSelection(subscribedProduct, event.target.checked)
                    }
                    required={false}
                    checked={selectedProducts.includes(subscribedProduct)}
                    label={getCheckboxLabelProduct(subscribedProduct)}
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
