import React, { ReactNode, Ref } from "react";
import { Button, Spinner } from "react-bootstrap";

interface TapirButtonProps {
  variant: string;
  text?: ReactNode;
  icon?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  disabled?: boolean;
  size?: "sm" | "lg";
  style?: React.CSSProperties;
  loading?: boolean;
  type?: "submit" | "reset" | "button";
  fontSize?: number;
  tooltip?: string;
  iconPosition?: "left" | "right";
  rotateIcon?: string;
  className?: string;
  ref?: Ref<HTMLButtonElement>;
}

const TapirButton: React.FC<TapirButtonProps> = (props) => {
  function textContent() {
    return props.loading ? "Laden..." : props.text;
  }

  function fontSize() {
    if (props.fontSize) {
      return props.fontSize + "px";
    }

    if (props.size === "sm") {
      return "16px";
    }

    return "";
  }

  function buildIcon() {
    if (!props.icon) return;

    if (props.loading) {
      return <Spinner size="sm" />;
    }

    return (
      <span
        className={"material-icons"}
        style={{
          fontSize: fontSize(),
          transform: props.rotateIcon
            ? "rotate(" + props.rotateIcon + "deg)"
            : "",
        }}
      >
        {props.icon}
      </span>
    );
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
      type={props.type ?? "button"}
      title={props.tooltip}
      className={props.className}
      ref={props.ref}
    >
      {(props.iconPosition === "left" || !props.iconPosition) && buildIcon()}
      {props.text &&
        (props.size == "sm" ? (
          <span>{textContent()}</span>
        ) : (
          <h5 className={"mb-0"}>{textContent()}</h5>
        ))}
      {props.iconPosition === "right" && buildIcon()}
    </Button>
  );
};

export default TapirButton;
