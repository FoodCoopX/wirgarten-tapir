import React from "react";
import { Table } from "react-bootstrap";
import { PaymentTransaction } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateMonthAndYear } from "../utils/formatDateMonthAndYear.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface PaymentTransactionsTableProps {
  transactions: PaymentTransaction[];
  setSelectedTransaction: (transaction: PaymentTransaction) => void;
}

function downloadFile(url: string) {
  const element = document.createElement("a");
  element.setAttribute("href", url);
  element.click();
}

const PaymentTransactionsTable: React.FC<PaymentTransactionsTableProps> = ({
  transactions,
  setSelectedTransaction,
}) => {
  return (
    <Table responsive hover striped bordered>
      <thead>
        <tr>
          <th>Monat</th>
          <th>Erstellt am</th>
          <th>Typ</th>
          <th>Anzahl</th>
          <th>Betrag</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {transactions.map((transaction) => (
          <tr key={transaction.id}>
            <td>{formatDateMonthAndYear(transaction.month)}</td>
            <td>{formatDateNumeric(transaction.createdAt)}</td>
            <td>{transaction.type}</td>
            <td>{transaction.paymentsCount}</td>
            <td>{formatCurrency(transaction.paymentsSum)}</td>
            <td>
              <div className={"d-flex flex-row gap-2"}>
                <TapirButton
                  text={"Details"}
                  icon={"visibility"}
                  variant={"outline-secondary"}
                  size={"sm"}
                  onClick={() => setSelectedTransaction(transaction)}
                />
                <TapirButton
                  text={"CSV-Datei runterladen"}
                  icon={"download"}
                  variant={"outline-secondary"}
                  size={"sm"}
                  onClick={() => downloadFile(transaction.csvDownloadUrl)}
                />
                <TapirButton
                  text={"XML-Datei runterladen"}
                  icon={"download"}
                  variant={"outline-secondary"}
                  size={"sm"}
                />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};

export default PaymentTransactionsTable;
