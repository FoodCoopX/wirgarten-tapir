import React from "react";
import { Modal } from "react-bootstrap";
import "dayjs/locale/de";
import TapirButton from "../../../components/TapirButton.tsx";
import { ProductForCancellation } from "../../../api-client";
import { formatDateText } from "../../../utils/formatDateText.ts";

interface CancellationStepConfirmationProps {
  selectedCancellationReasons: string[];
  selectedProducts: ProductForCancellation[];
  onConfirm: () => void;
  cancelCoopMembershipSelected: boolean;
  membershipText: string;
  customCancellationReasons: string | undefined;
  goToPreviousStep: () => void;
  confirmationLoading: boolean;
}

const CancellationStepConfirmation: React.FC<
  CancellationStepConfirmationProps
> = ({
  selectedCancellationReasons,
  selectedProducts,
  onConfirm,
  cancelCoopMembershipSelected,
  membershipText,
  customCancellationReasons,
  goToPreviousStep,
  confirmationLoading,
}) => {
  return (
    <>
      <Modal.Body>
        <p>Möchtest du wirklich folgenden Verträge kündigen?</p>
        <ul>
          {selectedProducts.map(
            (productForCancellation: ProductForCancellation) => {
              return (
                <li key={productForCancellation.product.id}>
                  {productForCancellation.product.type.name +
                    " (" +
                    productForCancellation.product.name +
                    ") zum " +
                    formatDateText(productForCancellation.cancellationDate)}
                </li>
              );
            },
          )}
          {cancelCoopMembershipSelected && <li>{membershipText}</li>}
        </ul>
        <p>Du hast folgende Gründe für die Kündigung genannt:</p>
        <ul>
          {selectedCancellationReasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
          {customCancellationReasons !== undefined && (
            <li>{customCancellationReasons}</li>
          )}
        </ul>
      </Modal.Body>
      <Modal.Footer>
        <div
          className={"d-flex flex-row justify-content-between"}
          style={{ width: "100%" }}
        >
          <TapirButton
            variant={"outline-secondary"}
            icon={"chevron_left"}
            text={"Zurück"}
            onClick={goToPreviousStep}
          />
          <TapirButton
            variant={"danger"}
            icon={"contract_delete"}
            text={"Kündigung bestätigen"}
            onClick={onConfirm}
            loading={confirmationLoading}
          />
        </div>
      </Modal.Footer>
    </>
  );
};

export default CancellationStepConfirmation;
