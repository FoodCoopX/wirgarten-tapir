import React from "react";
import TapirButton from "../../components/TapirButton.tsx";

interface NextButtonProps {
  onClick: () => void;
  disabled?: boolean;
  text?: string;
}

const NextStepButton: React.FC<NextButtonProps> = ({
  onClick,
  text,
  disabled,
}) => {
  return (
    <div
      style={{ height: "10dvh" }}
      className={"d-flex flex-column align-items-center justify-content-center"}
    >
      <TapirButton
        variant={"outline-secondary"}
        text={text ?? "Weiter"}
        onClick={onClick}
        size={"sm"}
        icon={"keyboard_arrow_down"}
        disabled={disabled ?? false}
        className={"nextStepButton"}
      />
    </div>
  );
};

export default NextStepButton;
