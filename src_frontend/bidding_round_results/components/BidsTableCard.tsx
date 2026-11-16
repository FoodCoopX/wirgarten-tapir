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
  rollbackAvailable: boolean;
  onRollbackAll: () => void;
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

const BidsTableCard: React.FC<BidsTableCardProps> = ({
  open,
  onToggle,
  roundId,
  members,
  rollbackAvailable,
  onRollbackAll,
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
              {isBidRange ? (
                <th className="text-nowrap">{"Grün/Rot (€/Monat)"}</th>
              ) : bidLevels > 1 ? (
                <th className="text-nowrap">
                  {interpolate("Gebot 1 – {count} (€/Monat)", {
                    count: bidLevels,
                  })}
                </th>
              ) : (
                <th className="text-nowrap">{"Betrag (€/Monat)"}</th>
              )}
              <th className="text-nowrap">
                {surchargeOnBids && surchargePercent > 0
                  ? isBidRange
                    ? interpolate("Effektiv (Pos. {position}, +{percent} %)", {
                        position: bidRangePosition,
                        percent: surchargePercent,
                      })
                    : interpolate("Effektiv (Stufe {level}, +{percent} %)", {
                        level: levelFromPosition(bidRangePosition, bidLevels),
                        percent: surchargePercent,
                      })
                  : isBidRange
                    ? interpolate("Effektiv (Pos. {position})", {
                        position: bidRangePosition,
                      })
                    : interpolate("Effektiv (Stufe {level})", {
                        level: levelFromPosition(bidRangePosition, bidLevels),
                      })}
              </th>
              <th className="text-nowrap">{"Abholort"}</th>
              <th>{"Aktualisiert"}</th>
              <th>{"Status"}</th>
              <th>{"Aktionen"}</th>
            </tr>
          </thead>
          <tbody>
            {members.map((entry) => (
              <tr key={entry.memberId}>
                <td>
                  {entry.bid && (
                    <Form.Check
                      checked={selectedBidIds.includes(entry.bid.id)}
                      onChange={() => onToggleBid(entry.bid?.id ?? null)}
                    />
                  )}
                  {!entry.hasBid && entry.isAutoRenewed && (
                    <Form.Check
                      checked={selectedAutoRenewedMemberIds.includes(
                        entry.memberId,
                      )}
                      onChange={() => onToggleAutoRenewedMember(entry.memberId)}
                    />
                  )}
                </td>
                <td>
                  <a href={`/tapir/members/${entry.memberId}`}>
                    {entry.memberName}
                  </a>
                </td>
                <td>
                  {entry.hasBid ? (
                    <span className="badge bg-success">{"Gebot"}</span>
                  ) : entry.isAutoRenewed ? (
                    <span className="badge bg-info text-dark">
                      {"Auto-verlängert"}
                    </span>
                  ) : (
                    <span className="badge bg-secondary">{"Kein Gebot"}</span>
                  )}
                </td>
                <td>
                  {entry.hasBid
                    ? renderMemberItems(entry.bid)
                    : entry.isAutoRenewed
                      ? renderContractItems(entry.autoRenewedItems ?? [])
                      : "–"}
                </td>
                <td>
                  {entry.bid
                    ? (isBidRange
                        ? ([1, 2] as const)
                        : Array.from(
                            { length: bidLevels },
                            (_, i) => (i + 1) as 1 | 2 | 3,
                          )
                      )
                        .map((level) =>
                          formatEuro(
                            bidAmountForLevel(entry.bid, level, isBidRange),
                          ),
                        )
                        .join(" / ")
                    : entry.isAutoRenewed
                      ? formatEuro(entry.autoRenewedAmountPerMonth)
                      : "–"}
                </td>
                <td>
                  {entry.bid ? (
                    <>
                      <div>
                        {formatEuro(
                          bidAmountAtPosition(
                            entry.bid,
                            bidRangePosition,
                            surchargeOnBids,
                            surchargeFactor,
                            isBidRange,
                          ),
                        )}{" "}
                        {"/ Monat"}
                      </div>
                      <div>
                        {formatEuro(
                          (bidAmountAtPosition(
                            entry.bid,
                            bidRangePosition,
                            surchargeOnBids,
                            surchargeFactor,
                            isBidRange,
                          ) ?? 0) * 12,
                        )}{" "}
                        {"/ Jahr"}
                      </div>
                    </>
                  ) : entry.isAutoRenewed ? (
                    <>
                      <div>
                        {formatEuro(entry.autoRenewedAmountPerMonth)}{" "}
                        {"/ Monat"}
                      </div>
                      <div>
                        {formatEuro(entry.autoRenewedAmountPerYear)} {"/ Jahr"}
                      </div>
                    </>
                  ) : (
                    "–"
                  )}
                </td>
                <td>
                  {entry.bid ? (
                    <>
                      <div>{entry.bid.pickupLocationName || "–"}</div>
                    </>
                  ) : entry.isAutoRenewed ? (
                    entry.autoRenewedPickupLocationName || "–"
                  ) : (
                    "–"
                  )}
                </td>
                <td>
                  {entry.bid?.updatedAt
                    ? new Date(entry.bid.updatedAt).toLocaleDateString("de-DE")
                    : "–"}
                </td>
                <td>
                  {entry.bid?.enteredByAdmin && (
                    <span className="badge bg-secondary me-1">
                      {"von Admin erfasst"}
                    </span>
                  )}
                  {entry.bid?.adminConfirmed ? (
                    <span className="text-success" title={"Admin-bestätigt"}>
                      {"✓"}
                    </span>
                  ) : (
                    entry.bid && (
                      <span className="badge bg-warning text-dark">
                        {"unbestätigt"}
                      </span>
                    )
                  )}
                </td>
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
        title={
          !averageBidLocked
            ? "Sperren Sie das Durchschnittsgebot, bevor Sie Verträge erzeugen."
            : !hasContractSelection
              ? "Wählen Sie zuerst mindestens ein Gebot oder einen Auto-Verlängerer aus."
              : undefined
        }
      >
        {"Verträge aus ausgewählten Geboten"}
      </Button>{" "}
      {!canOpenContractsModal &&
        (!averageBidLocked ? (
          <Button
            variant="link"
            className="p-0 align-baseline"
            onClick={onLockAverageBid}
          >
            {"Sperren Sie das Durchschnittsgebot, bevor Sie Verträge erzeugen."}
          </Button>
        ) : (
          <span className="text-danger small">
            {
              "Wählen Sie zuerst mindestens ein Gebot oder einen Auto-Verlängerer aus."
            }
          </span>
        ))}
      <a
        className="btn btn-outline-secondary"
        href={`/bidding_rounds/api/${roundId}/export.csv`}
      >
        {"CSV"}
      </a>
      {rollbackAvailable && (
        <Button variant="outline-danger" onClick={onRollbackAll}>
          {"Alle zurücknehmen"}
        </Button>
      )}
    </CollapsibleCard>
  );
};

export default BidsTableCard;
