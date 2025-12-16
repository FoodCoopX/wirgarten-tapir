import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import "dayjs/locale/de";
import { useApi } from "../../hooks/useApi.ts";
import { CoopApi, CoopShareTransaction } from "../../api-client";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import TapirButton from "../../components/TapirButton.tsx";

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
  const [bestellWizardUrl, setBestellWizardUrl] = useState("");

  useEffect(() => {
    loadShareData();
  }, []);

  function loadShareData() {
    setLoading(true);
    coopApi
      .coopApiGetCoopShareTransactionsRetrieve({ memberId: memberId })
      .then((response) => {
        setTransactions(response.transactions);
        setBestellWizardUrl(response.urlOfBestellWizard);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Geno-Anteile"),
      )
      .finally(() => setLoading(false));
  }

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

  function canBuyMoreShares() {
    if (transactions.length === 0) {
      return true;
    }

    for (const transaction of transactions) {
      if (
        transaction.transactionType === "purchase" ||
        transaction.transactionType === "transfer_in"
      ) {
        if (transaction.validAt < new Date()) {
          return true;
        }
      }
    }

    return false;
  }

  return (
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
                <tbody>
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
                          Number.parseInt(transaction.sharePrice) *
                            transaction.quantity,
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </small>
          </>
        )}
      </Card.Body>
      <Card.Footer>
        <div className={"d-flex justify-content-end"} style={{ width: "100%" }}>
          <TapirButton
            variant={"outline-primary"}
            icon={"add"}
            onClick={() => {
              canBuyMoreShares()
                ? location.assign(bestellWizardUrl)
                : alert(
                    "Du kannst weitere Genossenschaftsanteile erst zeichnen, wenn du formal Mitglied der Genossenschaft geworden bist.",
                  );
            }}
            loading={loading}
          />
        </div>
      </Card.Footer>
    </Card>
  );
};

export default CoopSharesCard;
