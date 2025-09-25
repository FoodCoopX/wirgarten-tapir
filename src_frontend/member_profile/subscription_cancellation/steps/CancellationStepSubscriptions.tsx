import React, { Dispatch, SetStateAction } from "react";
import { Form, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import { ProductForCancellation } from "../../../api-client";
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

  function getCheckboxLabel(subscribedProduct: ProductForCancellation) {
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
                    label={getCheckboxLabel(subscribedProduct)}
                  />
                </Form.Group>
              );
            },
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
            !cancelCoopMembershipSelected && selectedProducts.length === 0
          }
        />
      </Modal.Footer>
    </>
  );
};

export default CancellationStepSubscriptions;
