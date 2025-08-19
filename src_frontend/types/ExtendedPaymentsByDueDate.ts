import { ExtendedPayment } from "../api-client";

export type ExtendedPaymentsByDueDate = {
  [dueDateAsString: string]: ExtendedPayment[];
};
