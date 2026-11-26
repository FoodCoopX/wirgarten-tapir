import React from "react";
import { Badge, Button } from "react-bootstrap";
import { ButtonVariant } from "react-bootstrap/types";

interface TapirButtonProps {
  variant?: ButtonVariant;
  text?: string;
  icon?: React.ComponentType<{ style: any }>;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  disabled?: boolean;
  size?: "sm" | "lg" | undefined;
  style?: React.CSSProperties;
  notification?: number;
}

const TapirButton: React.FC<TapirButtonProps> = (props) => {
  return (
    <Button
      variant={props.variant ?? "undefined"}
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "2px",
        height: "100%",
        ...props.style,
      }}
      size={props.size}
      onClick={props.onClick}
      disabled={props.disabled}
    >
      <span>
        {props.text && <span>{props.text}</span>}
        {props.notification !== undefined && (
          <>
            {" "}
            <Badge bg={"secondary"}>{props.notification}</Badge>
          </>
        )}
        {props.icon && (
          <props.icon
            style={{
              width: "1.5em",
              marginLeft: props.text ? "0.25em" : "0em",
            }}
          />
        )}
      </span>
    </Button>
  );
};

export default TapirButton;
