import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import "dayjs/locale/de";
import { useApi } from "../../hooks/useApi.ts";
import { CoopApi, CoopShareTransaction } from "../../api-client";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";

interface CoopSharesCardProps {
  memberId: string;
  csrfToken: string;
}

const CoopSharesCard: React.FC<CoopSharesCardProps> = ({
  memberId,
  csrfToken,
}) => {
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState<CoopShareTransaction[]>([]);

  useEffect(() => {
    setLoading(true);
    coopApi
      .coopApiGetCoopShareTransactionsList({ memberId: memberId })
      .then(setTransactions)
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Geno-Anteile"),
      )
      .finally(() => setLoading(false));
  }, []);

  function getCurrentNumberOfShares(): number {
    return transactions.reduce(
      (sum, transaction) => sum + transaction.quantity,
      0,
    );
  }

  function getTransactionIcon(transaction: CoopShareTransaction) {
    switch (transaction.transactionType) {
      case "purchase":
        return "add";
      case "cancellation":
        return "remove";
      case "transfer_in":
        return "login";
      case "transfer_out":
        return "logout";
    }
  }
  return (
    <>
      <Card style={{ marginBottom: "1rem", textAlign: "center" }}>
        <Card.Body>
          {loading ? (
            <Spinner />
          ) : (
            <>
              <div className="contract-tile-number">
                <strong>{getCurrentNumberOfShares()}</strong> ×
              </div>
              <strong>Genossenschaftsanteile</strong>
              <hr />
              <small>
                <table style={{ width: "100%" }}>
                  {transactions.map((transaction) => (
                    <tr key={transaction.id}>
                      <td>
                        <span
                          className="material-icons"
                          style={{ fontSize: "1em" }}
                        >
                          {getTransactionIcon(transaction)}
                        </span>
                      </td>
                      <td>{formatDateNumeric(transaction.validAt)}</td>
                      <td style={{ textAlign: "right" }}>
                        {formatCurrency(
                          parseInt(transaction.sharePrice) *
                            transaction.quantity,
                        )}
                      </td>
                    </tr>
                  ))}
                </table>
              </small>
            </>
          )}
        </Card.Body>
        TODO CARD FOOTER WITH PURCHASE SHARES MODAL
      </Card>
    </>
  );
};

export default CoopSharesCard;
