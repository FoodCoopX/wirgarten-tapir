import { ExtendedPayment, MemberCredit } from "../../api-client";
import { TransactionsByDueDate } from "../../types/TransactionsByDueDate.ts";

export function sortGroupedTransactions(
  groupedTransactions: TransactionsByDueDate,
) {
  for (const key of Object.keys(groupedTransactions)) {
    groupedTransactions[key] =
      groupedTransactions[key].toSorted(compareTransactions);
  }
}

function compareTransactions(
  a: MemberCredit | ExtendedPayment,
  b: MemberCredit | ExtendedPayment,
) {
  const a_is_payment = "subscriptions" in a;
  const b_is_payment = "subscriptions" in b;
  if (a_is_payment !== b_is_payment) {
    return a_is_payment ? 1 : -1;
  }

  if (!a_is_payment || !b_is_payment) {
    return 0;
  }

  if (
    a.payment.subscriptionPaymentRangeStart &&
    b.payment.subscriptionPaymentRangeStart &&
    a.payment.subscriptionPaymentRangeStart !==
      b.payment.subscriptionPaymentRangeStart
  ) {
    return a.payment.subscriptionPaymentRangeStart.localeCompare(
      b.payment.subscriptionPaymentRangeStart,
    );
  }

  return b.payment.amount - a.payment.amount;
}
