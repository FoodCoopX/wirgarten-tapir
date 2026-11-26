import "@eonasdan/tempus-dominus/dist/css/tempus-dominus.min.css";
import "@fortawesome/fontawesome-free/css/fontawesome.css";
import "@fortawesome/fontawesome-free/css/solid.css";
import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React from "react";
import { Form } from "react-bootstrap";
import { TriggerDataRequest } from "tapir-api-client";
import TapirButton from "./TapirButton";
import TriggerInput from "./triggerInput";

interface MultipleTriggerInputProps {
  initialTriggers: TriggerDataRequest[];
  onChange: (triggers: TriggerDataRequest[]) => void;
  showError?: boolean;
}

const MultipleTriggerInput: React.FC<MultipleTriggerInputProps> = ({
  initialTriggers,
  onChange,
  showError = false,
}) => {
  const addNewTrigger = () => {
    onChange(
      initialTriggers.concat([{ triggerId: "", triggerFieldValues: {} }]),
    );
  };

  function onTriggerIdSelected(index: number, triggerId: string | null) {
    if (!triggerId) return;

    let newTriggers = [...initialTriggers];
    newTriggers[index].triggerId = triggerId;
    onChange(newTriggers);
  }

  function onTriggerFieldValuesChanged(index: number, fieldValues: any) {
    let newTriggers = [...initialTriggers];
    newTriggers[index].triggerFieldValues = fieldValues;
    onChange(newTriggers);
  }

  function onTriggerDeleteClicked(index: number) {
    let newTriggers = [...initialTriggers];
    newTriggers.splice(index, 1);
    onChange(newTriggers);
  }

  return (
    <div
      style={{
        backgroundColor: "var(--color-neutral-1)",
        padding: "1em",
        marginLeft: "-0.5em",
        marginRight: "-0.5em",
        borderRadius: "6px",
        border:
          "1px solid " +
          (showError
            ? "var(--bs-form-invalid-border-color)"
            : "var(--color-neutral-3)"),
      }}
      className="d-flex flex-column gap-2"
    >
      <Form.Label>Triggers</Form.Label>
      {initialTriggers.map((trigger, index) => (
        <TriggerInput
          key={index}
          onTriggerIdSelected={(triggerId) => {
            onTriggerIdSelected(index, triggerId);
          }}
          onTriggerFieldValuesChanged={(fieldValues) => {
            onTriggerFieldValuesChanged(index, fieldValues);
          }}
          triggerData={trigger}
          onTriggerDeleteClicked={() => {
            onTriggerDeleteClicked(index);
          }}
          allowDelete={initialTriggers.length > 1}
        />
      ))}
      {initialTriggers.some((t) => !t.triggerId) || (
        <TapirButton
          variant={"outline-success"}
          text={"Trigger hinzufügen"}
          icon={PlusCircleIcon}
          onClick={addNewTrigger}
        />
      )}
    </div>
  );
};

export default MultipleTriggerInput;
