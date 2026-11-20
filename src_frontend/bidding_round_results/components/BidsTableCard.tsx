import React from "react";
import { Button, Form, Table } from "react-bootstrap";

import { interpolate } from "../../utils/interpolate.ts";
import { formatEuro, levelFromPosition } from "../../utils/resultsFormat.ts";
import type { BidMemberSelection, BiddingRoundMemberRow } from "../types.ts";
import {
  bidAmountAtPosition,
  bidAmountForLevel,
  renderContractItems,
  renderMemberItems,
} from "../utils/bidFormatting.ts";
import CollapsibleCard from "./CollapsibleCard.tsx";

interface BidsTableCardProps {
  open: boolean;
  onToggle: () => void;
  roundId: string;
  members: BiddingRoundMemberRow[];
  autoRenewedEnabled: boolean;
  unconfirmedBidCount: number;
  isBidRange: boolean;
  bidLevels: number;
  bidRangePosition: number;
  surchargeOnBids: boolean;
  surchargePercent: number;
  surchargeFactor: number;
  filter: string;
  onFilterChange: (filter: string) => void;
  sort: string;
  onSortChange: (sort: string) => void;
  selectedBidIds: string[];
  selectedAutoRenewedMemberIds: string[];
  allDisplayedSelected: boolean;
  onToggleBid: (bidId: string | null) => void;
  onToggleAutoRenewedMember: (memberId: string) => void;
  onToggleAll: () => void;
  onConfirmBids: () => void;
  onConfirmAllBids: () => void;
  averageBidLocked: boolean;
  hasContractSelection: boolean;
  canOpenContractsModal: boolean;
  onOpenContractsModal: () => void;
  onLockAverageBid: () => void;
  onCreateBid: (member?: BidMemberSelection) => void;
  onEditBid: (entry: BiddingRoundMemberRow) => void;
  onDeleteBid: (entry: BiddingRoundMemberRow) => void;
}

function renderAmountHeader(isBidRange: boolean, bidLevels: number) {
  if (isBidRange) {
    return <th className="text-nowrap">{"Grün/Rot (€/Monat)"}</th>;
  }
  if (bidLevels > 1) {
    return (
      <th className="text-nowrap">
        {interpolate("Gebot 1 – {count} (€/Monat)", { count: bidLevels })}
      </th>
    );
  }
  return <th className="text-nowrap">{"Betrag (€/Monat)"}</th>;
}

function effectiveAmountHeader(
  isBidRange: boolean,
  bidRangePosition: number,
  bidLevels: number,
  surchargeOnBids: boolean,
  surchargePercent: number,
): string {
  const level = levelFromPosition(bidRangePosition, bidLevels);
  if (surchargeOnBids && surchargePercent > 0) {
    return isBidRange
      ? interpolate("Effektiv (Pos. {position}, +{percent} %)", {
          position: bidRangePosition,
          percent: surchargePercent,
        })
      : interpolate("Effektiv (Stufe {level}, +{percent} %)", {
          level,
          percent: surchargePercent,
        });
  }
  return isBidRange
    ? interpolate("Effektiv (Pos. {position})", {
        position: bidRangePosition,
      })
    : interpolate("Effektiv (Stufe {level})", { level });
}

function renderStatusBadge(entry: BiddingRoundMemberRow) {
  if (entry.hasBid) {
    return <span className="badge bg-success">{"Gebot"}</span>;
  }
  if (entry.isAutoRenewed) {
    return (
      <span className="badge bg-info text-dark">{"Auto-verlängert"}</span>
    );
  }
  return <span className="badge bg-secondary">{"Kein Gebot"}</span>;
}

function renderItems(entry: BiddingRoundMemberRow): string {
  if (entry.hasBid) {
    return renderMemberItems(entry.bid);
  }
  if (entry.isAutoRenewed) {
    return renderContractItems(entry.autoRenewedItems ?? []);
  }
  return "–";
}

function bidLevelsFor(
  isBidRange: boolean,
  bidLevels: number,
): readonly (1 | 2 | 3)[] {
  if (isBidRange) {
    return [1, 2] as const;
  }
  return Array.from({ length: bidLevels }, (_, i) => (i + 1) as 1 | 2 | 3);
}

function renderAmounts(
  entry: BiddingRoundMemberRow,
  isBidRange: boolean,
  bidLevels: number,
): string {
  if (entry.bid) {
    return bidLevelsFor(isBidRange, bidLevels)
      .map((level) =>
        formatEuro(bidAmountForLevel(entry.bid, level, isBidRange)),
      )
      .join(" / ");
  }
  if (entry.isAutoRenewed) {
    return formatEuro(entry.autoRenewedAmountPerMonth);
  }
  return "–";
}

function renderEffectiveAmount(
  entry: BiddingRoundMemberRow,
  isBidRange: boolean,
  bidRangePosition: number,
  surchargeOnBids: boolean,
  surchargeFactor: number,
) {
  if (entry.bid) {
    const monthly = bidAmountAtPosition(
      entry.bid,
      bidRangePosition,
      surchargeOnBids,
      surchargeFactor,
      isBidRange,
    );
    return (
      <>
        <div>
          {formatEuro(monthly)} {"/ Monat"}
        </div>
        <div>
          {formatEuro((monthly ?? 0) * 12)} {"/ Jahr"}
        </div>
      </>
    );
  }
  if (entry.isAutoRenewed) {
    return (
      <>
        <div>
          {formatEuro(entry.autoRenewedAmountPerMonth)} {"/ Monat"}
        </div>
        <div>{formatEuro(entry.autoRenewedAmountPerYear)} {"/ Jahr"}</div>
      </>
    );
  }
  return "–";
}

function renderPickupLocation(entry: BiddingRoundMemberRow): string {
  if (entry.bid) {
    return entry.bid.pickupLocationName || "–";
  }
  if (entry.isAutoRenewed) {
    return entry.autoRenewedPickupLocationName || "–";
  }
  return "–";
}

function renderUpdatedAt(entry: BiddingRoundMemberRow): string {
  if (!entry.bid?.updatedAt) {
    return "–";
  }
  return new Date(entry.bid.updatedAt).toLocaleDateString("de-DE");
}

function renderStatusCell(entry: BiddingRoundMemberRow) {
  return (
    <>
      {entry.bid?.enteredByAdmin && (
        <span className="badge bg-secondary me-1">{"von Admin erfasst"}</span>
      )}
      {entry.bid?.adminConfirmed ? (
        <span className="text-success" title={"Admin-bestätigt"}>
          {"✓"}
        </span>
      ) : (
        entry.bid && (
          <span className="badge bg-warning text-dark">{"unbestätigt"}</span>
        )
      )}
    </>
  );
}

interface BidsTableRowProps {
  entry: BiddingRoundMemberRow;
  isBidRange: boolean;
  bidLevels: number;
  bidRangePosition: number;
  surchargeOnBids: boolean;
  surchargeFactor: number;
  selectedBidIds: string[];
  selectedAutoRenewedMemberIds: string[];
  onToggleBid: (bidId: string | null) => void;
  onToggleAutoRenewedMember: (memberId: string) => void;
  onCreateBid: (member?: BidMemberSelection) => void;
  onEditBid: (entry: BiddingRoundMemberRow) => void;
  onDeleteBid: (entry: BiddingRoundMemberRow) => void;
}

const BidsTableRow: React.FC<BidsTableRowProps> = ({
  entry,
  isBidRange,
  bidLevels,
  bidRangePosition,
  surchargeOnBids,
  surchargeFactor,
  selectedBidIds,
  selectedAutoRenewedMemberIds,
  onToggleBid,
  onToggleAutoRenewedMember,
  onCreateBid,
  onEditBid,
  onDeleteBid,
}) => {
  return (
    <tr>
      <td>
        {entry.bid && (
          <Form.Check
            checked={selectedBidIds.includes(entry.bid.id)}
            onChange={() => onToggleBid(entry.bid?.id ?? null)}
          />
        )}
        {!entry.hasBid && entry.isAutoRenewed && (
          <Form.Check
            checked={selectedAutoRenewedMemberIds.includes(entry.memberId)}
            onChange={() => onToggleAutoRenewedMember(entry.memberId)}
          />
        )}
      </td>
      <td>
        <a href={`/tapir/members/${entry.memberId}`}>{entry.memberName}</a>
      </td>
      <td>{renderStatusBadge(entry)}</td>
      <td>{renderItems(entry)}</td>
      <td>{renderAmounts(entry, isBidRange, bidLevels)}</td>
      <td>
        {renderEffectiveAmount(
          entry,
          isBidRange,
          bidRangePosition,
          surchargeOnBids,
          surchargeFactor,
        )}
      </td>
      <td>{renderPickupLocation(entry)}</td>
      <td>{renderUpdatedAt(entry)}</td>
      <td>{renderStatusCell(entry)}</td>
      <td>
        {entry.bid ? (
          <div className="d-flex flex-row gap-1">
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={() => onEditBid(entry)}
            >
              {"Bearbeiten"}
            </Button>
            <Button
              variant="outline-danger"
              size="sm"
              onClick={() => onDeleteBid(entry)}
            >
              {"Löschen"}
            </Button>
          </div>
        ) : (
          <Button
            variant="outline-success"
            size="sm"
            onClick={() =>
              onCreateBid({
                memberId: entry.memberId,
                memberName: entry.memberName,
              })
            }
          >
            {"Gebot erfassen"}
          </Button>
        )}
      </td>
    </tr>
  );
};

function contractsButtonTitle(
  averageBidLocked: boolean,
  hasContractSelection: boolean,
): string | undefined {
  if (!averageBidLocked) {
    return "Sperren Sie das Durchschnittsgebot, bevor Sie Verträge erzeugen.";
  }
  if (!hasContractSelection) {
    return "Wählen Sie zuerst mindestens ein Gebot oder einen Auto-Verlängerer aus.";
  }
  return undefined;
}

interface ContractsHintProps {
  averageBidLocked: boolean;
  canOpenContractsModal: boolean;
  onLockAverageBid: () => void;
}

const ContractsHint: React.FC<ContractsHintProps> = ({
  averageBidLocked,
  canOpenContractsModal,
  onLockAverageBid,
}) => {
  if (canOpenContractsModal) {
    return null;
  }
  if (!averageBidLocked) {
    return (
      <Button
        variant="link"
        className="p-0 align-baseline"
        onClick={onLockAverageBid}
      >
        {"Sperren Sie das Durchschnittsgebot, bevor Sie Verträge erzeugen."}
      </Button>
    );
  }
  return (
    <span className="text-danger small">
      {
        "Wählen Sie zuerst mindestens ein Gebot oder einen Auto-Verlängerer aus."
      }
    </span>
  );
};

const BidsTableCard: React.FC<BidsTableCardProps> = ({
  open,
  onToggle,
  roundId,
  members,
  autoRenewedEnabled,
  unconfirmedBidCount,
  isBidRange,
  bidLevels,
  bidRangePosition,
  surchargeOnBids,
  surchargePercent,
  surchargeFactor,
  filter,
  onFilterChange,
  sort,
  onSortChange,
  selectedBidIds,
  selectedAutoRenewedMemberIds,
  allDisplayedSelected,
  onToggleBid,
  onToggleAutoRenewedMember,
  onToggleAll,
  onConfirmBids,
  onConfirmAllBids,
  averageBidLocked,
  hasContractSelection,
  canOpenContractsModal,
  onOpenContractsModal,
  onLockAverageBid,
  onCreateBid,
  onEditBid,
  onDeleteBid,
}) => {
  return (
    <CollapsibleCard title={"Gebote"} open={open} onToggle={onToggle}>
      <div className="d-flex flex-row justify-content-end align-items-center">
        <div className="d-flex gap-2">
          <Form.Select
            size="sm"
            value={filter}
            onChange={(event) => onFilterChange(event.target.value)}
          >
            <option value="active_in_contract_period">
              {"Aktive Mitglieder (Vertragsperiode)"}
            </option>
            <option value="all">{"Alle Mitglieder"}</option>
            <option value="has_bid">{"Hat geboten"}</option>
            <option value="no_bid">{"Hat nicht geboten"}</option>
            {autoRenewedEnabled && (
              <option value="auto_renewed">{"Auto-verlängert"}</option>
            )}
          </Form.Select>
          <Form.Select
            size="sm"
            value={sort}
            onChange={(event) => onSortChange(event.target.value)}
          >
            <option value="name">{"Sortierung: Name"}</option>
            <option value="date">{"Sortierung: Datum"}</option>
          </Form.Select>
          <Button
            variant="outline-dark"
            size="sm"
            onClick={onConfirmAllBids}
            disabled={!unconfirmedBidCount}
          >
            {"Alle bestätigen"}
          </Button>
          <Button
            variant="outline-success"
            size="sm"
            onClick={() => onCreateBid()}
          >
            {"Gebot erfassen"}
          </Button>
        </div>
      </div>
      {members.length > 0 ? (
        <Table
          striped
          hover
          size="sm"
          className="mt-2"
          responsive
          style={{ fontSize: "0.8rem" }}
        >
          <thead>
            <tr>
              <th>
                <Form.Check
                  checked={allDisplayedSelected}
                  onChange={onToggleAll}
                />
              </th>
              <th>{"Mitglied"}</th>
              <th>{"Gebot"}</th>
              <th>{"Positionen"}</th>
              {renderAmountHeader(isBidRange, bidLevels)}
              <th className="text-nowrap">
                {effectiveAmountHeader(
                  isBidRange,
                  bidRangePosition,
                  bidLevels,
                  surchargeOnBids,
                  surchargePercent,
                )}
              </th>
              <th className="text-nowrap">{"Abholort"}</th>
              <th>{"Aktualisiert"}</th>
              <th>{"Status"}</th>
              <th>{"Aktionen"}</th>
            </tr>
          </thead>
          <tbody>
            {members.map((entry) => (
              <BidsTableRow
                key={entry.memberId}
                entry={entry}
                isBidRange={isBidRange}
                bidLevels={bidLevels}
                bidRangePosition={bidRangePosition}
                surchargeOnBids={surchargeOnBids}
                surchargeFactor={surchargeFactor}
                selectedBidIds={selectedBidIds}
                selectedAutoRenewedMemberIds={selectedAutoRenewedMemberIds}
                onToggleBid={onToggleBid}
                onToggleAutoRenewedMember={onToggleAutoRenewedMember}
                onCreateBid={onCreateBid}
                onEditBid={onEditBid}
                onDeleteBid={onDeleteBid}
              />
            ))}
          </tbody>
        </Table>
      ) : (
        <p>{"Keine Mitglieder vorhanden."}</p>
      )}
      <Button
        variant="success"
        onClick={onConfirmBids}
        disabled={selectedBidIds.length === 0}
      >
        {"Ausgewählte bestätigen"}
      </Button>{" "}
      <Button
        variant="primary"
        onClick={onOpenContractsModal}
        disabled={!canOpenContractsModal}
        title={contractsButtonTitle(averageBidLocked, hasContractSelection)}
      >
        {"Verträge aus ausgewählten Geboten"}
      </Button>{" "}
      <ContractsHint
        averageBidLocked={averageBidLocked}
        canOpenContractsModal={canOpenContractsModal}
        onLockAverageBid={onLockAverageBid}
      />
      <a
        className="btn btn-outline-secondary"
        href={`/bidding_rounds/api/${roundId}/export.csv`}
      >
        {"CSV"}
      </a>
    </CollapsibleCard>
  );
};

export default BidsTableCard;
