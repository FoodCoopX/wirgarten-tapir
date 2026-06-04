import React, { useEffect, useState } from "react";
import { Card, Table } from "react-bootstrap";
import { PaymentsApi, PaymentTransaction } from "../api-client";
import BootstrapPagination from "../components/pagination/BootstrapPagination.tsx";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import PaymentTransactionDetailsModal from "./PaymentTransactionDetailsModal.tsx";
import PaymentTransactionTable from "./PaymentTransactionTable.tsx";

interface PaymentTransactionsBaseProps {
  csrfToken: string;
}

const PaymentTransactionsBase: React.FC<PaymentTransactionsBaseProps> = ({
  csrfToken,
}) => {
  const api = useApi(PaymentsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalNumberOfTransactions, setTotalNumberOfTransactions] = useState(0);
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [selectedTransaction, setSelectedTransaction] = useState<
    PaymentTransaction | undefined
  >(undefined);

  useEffect(() => {
    api
      .paymentsPaymentTransactionsList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
      })
      .then((response) => {
        setTransactions(response.results);
        setTotalNumberOfTransactions(response.count);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Lastschriften",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [currentPage]);

  return (
    <>
      <Card className={"mt-4"}>
        <Card.Header>
          <div
            className={"d-flex justify-content-between align-items-center mb-0"}
          >
            <h5 className={"mb-0"}>Zahlungseingang</h5>
          </div>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <Table responsive hover bordered>
              <tbody>
                <PlaceholderTableRows nbRows={10} nbColumns={6} size={"lg"} />
              </tbody>
            </Table>
          ) : (
            <PaymentTransactionTable
              transactions={transactions}
              setSelectedTransaction={setSelectedTransaction}
            />
          )}
        </Card.Body>
        <Card.Footer>
          <div
            className={"d-flex justify-content-center"}
            style={{ width: "100%" }}
          >
            <BootstrapPagination
              currentPage={currentPage}
              pageSize={DEFAULT_PAGE_SIZE}
              itemCount={totalNumberOfTransactions}
              goToPage={setCurrentPage}
            />
          </div>
        </Card.Footer>
      </Card>
      {selectedTransaction && (
        <PaymentTransactionDetailsModal
          transaction={selectedTransaction}
          onHide={() => setSelectedTransaction(undefined)}
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default PaymentTransactionsBase;
