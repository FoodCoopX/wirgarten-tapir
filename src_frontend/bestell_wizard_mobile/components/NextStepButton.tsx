import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { NEXT_BUTTON_HEIGHT } from "../utils/DIMENSIONS.ts";

interface NextButtonProps {
  onClick: () => void;
  disabled?: boolean;
  text?: string;
  showError?: boolean;
  loading?: boolean;
  isOrderStep?: boolean;
}

const NextStepButton: React.FC<NextButtonProps> = ({
  onClick,
  text,
  disabled,
  showError,
  loading,
  isOrderStep,
}) => {
  function getButtonText() {
    if (text) {
      return text;
    }
    if (isOrderStep) {
      return "Bestellung bestätigen";
    }
    return "Weiter";
  }

  function getVariant() {
    if (showError) {
      return "outline-danger";
    }

    if (isOrderStep) {
      return "dark";
    }

    return BUTTON_VARIANT;
  }

  return (
    <div
      style={{ height: NEXT_BUTTON_HEIGHT + "dvh" }}
      className={"d-flex flex-column align-items-center justify-content-center"}
    >
      <TapirButton
        variant={getVariant()}
        text={getButtonText()}
        onClick={onClick}
        icon={isOrderStep ? "done_all" : "keyboard_arrow_down"}
        disabled={disabled ?? false}
        className={"nextStepButton"}
        loading={loading}
      />
    </div>
  );
};

export default NextStepButton;
