import React from "react";
import { Button, Spinner } from "react-bootstrap";

interface TapirButtonProps {
  variant: string;
  text?: string;
  icon?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  disabled?: boolean;
  size?: "sm" | "lg";
  style?: React.CSSProperties;
  loading?: boolean;
  type?: "submit" | "reset" | "button";
}

const TapirButton: React.FC<TapirButtonProps> = (props) => {
  function textContent() {
    return props.loading ? "Loading..." : props.text;
  }

  return (
    <Button
      variant={props.variant ?? "undefined"}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        ...props.style,
      }}
      size={props.size}
      onClick={props.onClick}
      disabled={props.disabled || props.loading}
      type={props.type}
    >
      {props.icon &&
        (props.loading ? (
          <Spinner size="sm" />
        ) : (
          <span className={"material-icons"} style={{ fontSize: "16px" }}>
            {props.icon}
          </span>
        ))}
      {props.text &&
        (props.size == "sm" ? (
          <span>{textContent()}</span>
        ) : (
          <h5 className={"mb-0"}>{textContent()}</h5>
        ))}
    </Button>
  );
};

export default TapirButton;
