import React from "react";
import { Alert, Button, Form, Modal, Spinner, Table } from "react-bootstrap";

import type { BiddableProduct } from "../../api-client/models/BiddableProduct.ts";
import { formatEuro, formatNumber } from "../../utils/resultsFormat.ts";
import type {
  BiddingRoundContractRow,
  ContractCreationError,
} from "../types.ts";
import { renderContractItems } from "../utils/bidFormatting.ts";
import CollapsibleCard from "./CollapsibleCard.tsx";

interface ContractsCardProps {
  open: boolean;
  onToggle: () => void;
  contracts: BiddingRoundContractRow[];
  growingPeriodId: string | null;
  rollbackAvailable: boolean;
  rollbackUntracked: boolean;
  onRollback: (memberIds: string[], memberNames: string[]) => void;
}

const isSolidarityRound = true;

const ContractsCard: React.FC<ContractsCardProps> = ({
  open,
  onToggle,
  contracts,
  growingPeriodId,
  rollbackUntracked,
  onRollback,
}) => {
  return (
    <CollapsibleCard
      title={"Erzeugte Verträge"}
      open={open}
      onToggle={onToggle}
    >
      <Table size="sm" responsive>
        <thead>
          <tr>
            <th>{"Mitglied"}</th>
            <th>{"Status"}</th>
            <th>{"Positionen"}</th>
            <th className="text-end">{"Gebote (Stufen)"}</th>
            <th className="text-end">{"Gebot (berechnet, pro Anteil)"}</th>
            <th className="text-end">{"Vorher / Monat"}</th>
            {isSolidarityRound && (
              <th className="text-end">{"Vertragspreis / Monat"}</th>
            )}
            {isSolidarityRound && (
              <th className="text-end">{"Non-Bidder-Floor / Monat"}</th>
            )}
            {isSolidarityRound && (
              <th className="text-end">{"Solidaritätsbeitrag / Monat"}</th>
            )}
            <th className="text-end">{"Gesamt / Monat"}</th>
            <th className="text-end">{"Gesamt / Jahr"}</th>
            <th>{"Verteilstation"}</th>
            <th>{"Vertrag"}</th>
            <th>{"Aktion"}</th>
          </tr>
        </thead>
        <tbody>
          {contracts.map((contract) => (
            <tr key={contract.memberId}>
              <td>
                <a
                  href={`/tapir/members/${contract.memberId}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {contract.memberName}
                </a>
              </td>
              <td>
                {contract.type === "auto_renewed" ? (
                  <span className="badge bg-secondary">
                    {"Bietrunde: Auto-Verlängert"}
                  </span>
                ) : (
                  <span className="badge bg-success">{"Bietrunde: Gebot"}</span>
                )}
              </td>
              <td>{renderContractItems(contract.items)}</td>
              <td className="text-end">
                {contract.bidAmounts && contract.bidAmounts.length > 0
                  ? contract.bidAmounts
                      .map((amount) => formatEuro(Number(amount)))
                      .join(" / ")
                  : "–"}
              </td>
              <td className="text-end">
                {contract.bidEffectiveAmount != null
                  ? formatEuro(Number(contract.bidEffectiveAmount))
                  : "–"}
              </td>
              <td className="text-end">
                {contract.type === "auto_renewed" &&
                contract.previousAmountPerMonth != null
                  ? formatEuro(Number(contract.previousAmountPerMonth))
                  : "–"}
              </td>
              {isSolidarityRound && (
                <td className="text-end">
                  {formatEuro(Number(contract.standardAmountPerMonth))}
                </td>
              )}
              {isSolidarityRound && (
                <td className="text-end">
                  {contract.nonBidderFloorPerMonth != null
                    ? formatEuro(Number(contract.nonBidderFloorPerMonth))
                    : "–"}
                </td>
              )}
              {isSolidarityRound && (
                <td className="text-end">
                  {formatEuro(Number(contract.contributionAmountPerMonth))}
                </td>
              )}
              <td className="text-end">
                {formatEuro(Number(contract.amountPerMonth))}
              </td>
              <td className="text-end">
                {formatEuro(Number(contract.amountPerYear))}
              </td>
              <td>{contract.pickupLocationName || "–"}</td>
              <td>
                <a
                  href={`/tapir/contracts?period=${growingPeriodId}&member=${contract.memberId}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {"Vertrag"}
                </a>
              </td>
              <td>
                {contract.rollbackState === "applied" && (
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() =>
                      onRollback([contract.memberId], [contract.memberName])
                    }
                  >
                    {"Zurücknehmen"}
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      {rollbackUntracked && (
        <p className="text-muted small mt-2 mb-0">
          {
            "Diese Runde wurde vor der Effekt-Aufzeichnung erzeugt. Eine automatische Rücknahme ist nicht möglich; bitte manuell prüfen."
          }
        </p>
      )}
    </CollapsibleCard>
  );
};

interface CreateContractsModalProps {
  show: boolean;
  onHide: () => void;
  growingPeriodId: string | null;
  biddableProduct: BiddableProduct | null;
  biddersAveragePerMonth: number | null;
  checkLoading: boolean;
  checkMessage: string | null;
  checkErrors: ContractCreationError[];
  selectedBidsConfirmed: boolean;
  createAutoRenewed: boolean;
  onCreateAutoRenewedChange: (value: boolean) => void;
  createLoading: boolean;
  onRunCheck: () => void;
  onCreateContracts: () => void;
  standardPriceSaving: boolean;
  onAlignStandardPrices: () => void;
}

export const CreateContractsModal: React.FC<CreateContractsModalProps> = ({
  show,
  onHide,
  growingPeriodId,
  biddableProduct,
  biddersAveragePerMonth,
  checkLoading,
  checkMessage,
  checkErrors,
  selectedBidsConfirmed,
  createAutoRenewed,
  onCreateAutoRenewedChange,
  createLoading,
  onRunCheck,
  onCreateContracts,
  standardPriceSaving,
  onAlignStandardPrices,
}) => {
  return (
    <Modal show={show} onHide={onHide} centered={true} size="lg">
      <Modal.Header closeButton>
        <h5 className="mb-0">{"Verträge erzeugen"}</h5>
      </Modal.Header>
      <Modal.Body>
        {(biddableProduct?.products?.length ?? 0) > 0 &&
          biddersAveragePerMonth != null && (
            <Alert variant="info" className="border border-info">
              <div className="fw-bold mb-1">
                {"Hinweis: Standardpreis und Durchschnittsgebot"}
              </div>
              <ul className="mb-0">
                {biddableProduct?.products.map((product) => {
                  const size = Number(product.size ?? 1);
                  return (
                    <li key={product.id}>
                      {product.name}: Vertragsperiode Standardpreis{" "}
                      {formatEuro(Number(product.standardPrice ?? 0))} / Monat,
                      Bietrunde Richtwert{" "}
                      {formatEuro(Number(product.referenceValue ?? 0))} / Monat,
                      Durchschnittsgebot{" "}
                      {formatEuro(biddersAveragePerMonth * size)} / Monat (Größe{" "}
                      {formatNumber(product.size)}).
                    </li>
                  );
                })}
              </ul>
              <div className="d-flex flex-wrap align-items-center gap-2 mt-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={onAlignStandardPrices}
                  disabled={standardPriceSaving}
                >
                  {standardPriceSaving ? (
                    <Spinner animation="border" size="sm" />
                  ) : (
                    "Standardpreis angleichen"
                  )}
                </Button>
                {growingPeriodId && (
                  <a
                    href={`/tapir/product?periodId=${growingPeriodId}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {"Vertragsperiode öffnen"}
                  </a>
                )}
              </div>
            </Alert>
          )}
        {checkLoading ? (
          <div className="d-flex align-items-center gap-2">
            <Spinner animation="border" size="sm" />
            <span>{"Verträge werden geprüft…"}</span>
          </div>
        ) : (
          <>
            {!selectedBidsConfirmed && (
              <p className="text-danger small mb-2">
                {
                  "Alle ausgewählten Gebote müssen bestätigt sein, bevor Verträge erzeugt werden. Prüfen Sie die Liste unten."
                }
              </p>
            )}
            {checkMessage && <p className="mb-2">{checkMessage}</p>}
            {checkErrors.length > 0 && (
              <Table size="sm" responsive>
                <thead>
                  <tr>
                    <th>{"Mitglied"}</th>
                    <th>{"Produkt"}</th>
                    <th>{"Grund"}</th>
                  </tr>
                </thead>
                <tbody>
                  {checkErrors.map((error) => (
                    <tr
                      key={`${error.memberId}:${error.productName ?? ""}:${error.error ?? ""}`}
                    >
                      <td>{error.memberName ?? error.memberId}</td>
                      <td>{error.productName ?? "–"}</td>
                      <td>{error.error ?? "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
            <hr />
            <Form.Check
              type="switch"
              id="create-auto-renewed-switch"
              label={
                "Auch Auto-Verlängerer-Verträge vor Ablauf der Kündigungsfrist anlegen"
              }
              checked={createAutoRenewed}
              onChange={(event) =>
                onCreateAutoRenewedChange(event.target.checked)
              }
            />
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button
          variant="outline-primary"
          onClick={onRunCheck}
          disabled={checkLoading || createLoading}
        >
          {"Verträge prüfen"}
        </Button>
        <Button
          variant="primary"
          onClick={onCreateContracts}
          disabled={checkLoading || createLoading || !selectedBidsConfirmed}
        >
          {createLoading ? (
            <Spinner animation="border" size="sm" />
          ) : (
            "Verträge erzeugen"
          )}
        </Button>
        <Button variant="secondary" onClick={onHide} disabled={createLoading}>
          {"Abbrechen"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default ContractsCard;
