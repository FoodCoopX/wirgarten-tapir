import React, { ReactNode } from "react";
import { OverlayTrigger, Popover } from "react-bootstrap";
import TapirButton from "./TapirButton.tsx";

interface TapirHelpButtonProps {
  title?: string;
  text: ReactNode;
  buttonSize?: "sm" | "lg";
  width?: string;
}

const TapirHelpButton: React.FC<TapirHelpButtonProps> = ({
  title,
  text,
  buttonSize,
  width,
}) => {
  function buildTooltip() {
    return (
      <Popover id="popover-basic" style={{ maxWidth: width ?? "500px" }}>
        <Popover.Header as="h3">{title ?? "Erklärung"}</Popover.Header>
        <Popover.Body>{text}</Popover.Body>
      </Popover>
    );
  }

  return (
    <OverlayTrigger
      overlay={buildTooltip()}
      trigger={"click"}
      placement={"bottom"}
      rootClose={true}
    >
      <TapirButton
        variant={"outline-secondary"}
        icon={"help"}
        size={buttonSize}
      />
    </OverlayTrigger>
  );
};

export default TapirHelpButton;
