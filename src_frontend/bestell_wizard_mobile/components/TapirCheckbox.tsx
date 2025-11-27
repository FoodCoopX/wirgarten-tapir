import React from "react";
import "./tapir_checkbox.css";

interface NextButtonProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  controlId: string;
  label?: string;
  disabled?: boolean;
}

const TapirCheckbox: React.FC<NextButtonProps> = ({
  checked,
  onChange,
  controlId,
  label,
  disabled,
}) => {
  return (
    <div className={"d-flex flex-row gap-2"}>
      <input
        type={"checkbox"}
        className={"inp-cbx"}
        style={{ display: "none" }}
        id={controlId}
        checked={checked}
        onChange={(event) => {
          onChange(event.target.checked);
        }}
        disabled={disabled}
      />
      <label
        className={"cbx d-flex flex-row align-items-center"}
        htmlFor={controlId}
      >
        <span style={{ flexShrink: 0 }}>
          <svg width={"12px"} height={"10px"} viewBox={"0 0 12 10"}>
            <polyline points={"1.5 6 4.5 9 10.5 1"} />
          </svg>
        </span>
        {label && <span>{label}</span>}
      </label>
    </div>
  );
};

export default TapirCheckbox;
