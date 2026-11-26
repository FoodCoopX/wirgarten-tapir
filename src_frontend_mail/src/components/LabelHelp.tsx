import { QuestionMarkCircleIcon } from "@heroicons/react/24/outline";
import React, { ReactNode, useId } from "react";
import TapirTooltip from "./TapirTooltip";

interface LabelHelpProps {
  label: string;
  text: ReactNode;
}

const LabelHelp: React.FC<LabelHelpProps> = ({ label, text }) => {
  const id = useId().replace(/:/g, "");

  return (
    <TapirTooltip id={`label-help-${id}`} text={text} placement="right">
      <span
        role="img"
        aria-label={`Hilfe zu ${label}`}
        tabIndex={0}
        className="text-muted"
        style={{
          display: "inline-flex",
          alignItems: "center",
          marginLeft: "0.25em",
          cursor: "help",
          verticalAlign: "middle",
        }}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
        onKeyDown={(event) => event.stopPropagation()}
      >
        <QuestionMarkCircleIcon width={16} height={16} />
      </span>
    </TapirTooltip>
  );
};

export default LabelHelp;
