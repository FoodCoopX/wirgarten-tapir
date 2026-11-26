import React, { ReactNode } from "react";

import OverlayTrigger from "react-bootstrap/OverlayTrigger";
import Tooltip from "react-bootstrap/Tooltip";

interface TapirTooltipProps {
  id: string;
  children: ReactNode;
  text: ReactNode;
  enabled?: boolean;
  placement?: "auto" | "top" | "bottom" | "left" | "right";
}

const TapirTooltip: React.FC<TapirTooltipProps> = ({
  id,
  children,
  text,
  enabled = true,
  placement,
}) => {
  const overlay = enabled ? <Tooltip id={id}>{text}</Tooltip> : <></>;
  return (
    <OverlayTrigger overlay={overlay} placement={placement}>
      <span>{children}</span>
    </OverlayTrigger>
  );
};

export default TapirTooltip;
