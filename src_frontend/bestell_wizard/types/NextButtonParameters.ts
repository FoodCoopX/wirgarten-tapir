import { ButtonVariant } from "react-bootstrap/types";

export interface NextButtonParameters {
  icon?: string;
  text?: string;
  disabled: boolean;
  loading: boolean;
  variant?: ButtonVariant;
}
