import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import TapirButton from "../../../components/TapirButton.tsx";

interface CancellationStepReasonsProps {
  defaultCancellationReasons: string[];
  selectedCancellationReasons: string[];
  customCancellationReason: string | undefined;
  setSelectedCancellationReasons: (cancellationReasons: string[]) => void;
  setCustomCancellationReason: (
    cancellationReasons: string | undefined,
  ) => void;
  goToNextStep: () => void;
  goToPreviousStep: () => void;
}

const CancellationStepReasons: React.FC<CancellationStepReasonsProps> = ({
  defaultCancellationReasons,
  selectedCancellationReasons,
  customCancellationReason,
  setSelectedCancellationReasons,
  setCustomCancellationReason,
  goToNextStep,
  goToPreviousStep,
}) => {
  const [customCancellationReasonEnabled, setCustomCancellationReasonEnabled] =
    useState(false);

  useEffect(() => {
    if (!customCancellationReasonEnabled) {
      setCustomCancellationReason(undefined);
    }
  }, [customCancellationReasonEnabled]);

  function changeSelection(reason: string, selected: boolean) {
    if (selected && !selectedCancellationReasons.includes(reason)) {
      setSelectedCancellationReasons([...selectedCancellationReasons, reason]);
    } else if (!selected && selectedCancellationReasons.includes(reason)) {
      setSelectedCancellationReasons(
        selectedCancellationReasons.filter((r) => r !== reason),
      );
    }
  }

  return (
    <>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"subscriptionCancellationReasonsModalForm"}
        >
          <div>Warum möchtest du deinen Vertrag kündigen?</div>

          {defaultCancellationReasons.map((reason) => {
            return (
              <Form.Group key={reason} controlId={reason}>
                <Form.Check
                  onChange={(event) =>
                    changeSelection(reason, event.target.checked)
                  }
                  checked={selectedCancellationReasons.includes(reason)}
                  label={reason}
                />
              </Form.Group>
            );
          })}

          <Form.Group controlId={"custom"}>
            <Form.Check
              onChange={(event) =>
                setCustomCancellationReasonEnabled(event.target.checked)
              }
              checked={customCancellationReasonEnabled}
              label={"Sonstiges:"}
            />
          </Form.Group>
          {customCancellationReasonEnabled && (
            <Form.Group controlId={"custom"}>
              <Form.Control
                onChange={(event) =>
                  setCustomCancellationReason(event.target.value)
                }
              />
            </Form.Group>
          )}
        </Form>
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
            variant={"outline-danger"}
            icon={"contract_delete"}
            text={"Weiter"}
            onClick={goToNextStep}
            disabled={
              selectedCancellationReasons.length === 0 &&
              (customCancellationReason === undefined ||
                customCancellationReason.trim() === "")
            }
          />
        </div>
      </Modal.Footer>
    </>
  );
};

export default CancellationStepReasons;
