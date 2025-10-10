import { ExtendedPayment, MemberCredit } from "../api-client";

export type TransactionsByDueDate = {
  [dueDateAsString: string]: (ExtendedPayment | MemberCredit)[];
};
