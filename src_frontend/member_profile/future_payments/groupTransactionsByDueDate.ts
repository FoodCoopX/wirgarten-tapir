import dayjs from "dayjs";
import { ExtendedPayment, MemberCredit } from "../../api-client";
import { TransactionsByDueDate } from "../../types/TransactionsByDueDate.ts";
import { sortGroupedTransactions } from "./sortGroupedTransactions.ts";

export function groupTransactionsByDueDate(
  extendedPayments: ExtendedPayment[],
  memberCredits: MemberCredit[],
): TransactionsByDueDate {
  const groupedTransactions: TransactionsByDueDate = {};

  for (const extendedPayment of extendedPayments) {
    const dueDateAsAstring = dayjs(extendedPayment.payment.dueDate).format(
      "YYYY-MM-DD",
    );
    if (!(dueDateAsAstring in groupedTransactions)) {
      groupedTransactions[dueDateAsAstring] = [];
    }
    groupedTransactions[dueDateAsAstring].push(extendedPayment);
  }

  for (const memberCredit of memberCredits) {
    const dueDateAsAstring = dayjs(memberCredit.dueDate).format("YYYY-MM-DD");
    if (!(dueDateAsAstring in groupedTransactions)) {
      groupedTransactions[dueDateAsAstring] = [];
    }
    groupedTransactions[dueDateAsAstring].push(memberCredit);
  }

  sortGroupedTransactions(groupedTransactions);

  return groupedTransactions;
}
