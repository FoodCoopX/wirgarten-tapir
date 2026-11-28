import React, { FC } from "react";
import { useAccordionButton } from "react-bootstrap";

type AccordionToggleCompactProps = {
  children: React.ReactNode;
  eventKey: string;
  style?: React.CSSProperties;
  customOnClick?: () => void;
};

const AccordionToggleCompact: FC<AccordionToggleCompactProps> = ({
  children,
  eventKey,
  style = {},
  customOnClick = () => {},
}) => {
  const decoratedOnClick = useAccordionButton(eventKey, customOnClick);

  return (
    <div
      style={{
        width: "100%",
        margin: "0.5em",
        alignItems: "center",
        cursor: "pointer",
        userSelect: "none",
        textAlign: "center",
        flexGrow: 1,
        ...style,
      }}
      onClick={decoratedOnClick}
    >
      {children}
    </div>
  );
};

export default AccordionToggleCompact;
