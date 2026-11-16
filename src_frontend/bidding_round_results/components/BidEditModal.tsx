import React, { useEffect, useState } from "react";
import { Button, Form, Modal } from "react-bootstrap";

import type { Bid } from "../../api-client/models/Bid.ts";
import type { BiddableProduct } from "../../api-client/models/BiddableProduct.ts";
import type { ResultsTableMember } from "../../api-client/models/ResultsTableMember.ts";
import {
  BID_RANGE_LEVELS,
  getBidRangeDefaultLabel,
} from "../../bidding_round/utils/bidRangeLevels.ts";
import { interpolate } from "../../utils/interpolate.ts";
import type {
  BidFormPayload,
  BidItemDraft,
  BidItemPayload,
  BidMemberSelection,
} from "../types.ts";

interface BidEditModalProps {
  show: boolean;
  onHide: () => void;
  editingBid: Bid | null;
  member: BidMemberSelection;
  members: ResultsTableMember[];
  biddableProduct: BiddableProduct | null;
  bidLevels: number;
  isBidRange: boolean;
  quantityEnabled: boolean;
  saving: boolean;
  onSave: (payload: BidFormPayload) => void;
}

function defaultAmounts(
  value: string | null,
  bidLevels: number,
): Partial<BidItemDraft> {
  const levels = Math.min(Math.max(bidLevels, 1), 3);
  return {
    amount1: value,
    ...(levels >= 2 ? { amount2: value } : {}),
    ...(levels >= 3 ? { amount3: value } : {}),
  };
}

function emptyBidItems(
  biddableProduct: BiddableProduct | null,
  bidLevels: number,
): BidItemDraft[] {
  const product = biddableProduct?.products[0];
  if (!biddableProduct || !product) return [];
  return [
    {
      roundProductTypeId: biddableProduct.id,
      productId: product.id,
      quantity: 1,
      ...defaultAmounts("", bidLevels),
    },
  ];
}

function bidToDraftItems(bid: Bid, isBidRange: boolean): BidItemDraft[] {
  return (bid.items ?? []).map((item) => ({
    roundProductTypeId: item.roundProductTypeId,
    productId: item.productId,
    quantity: item.quantity,
    amount1: item.amount1 ?? null,
    amount2: item.amount2 ?? null,
    amount3: isBidRange ? null : (item.amount3 ?? null),
  }));
}

const BidEditModal: React.FC<BidEditModalProps> = ({
  show,
  onHide,
  editingBid,
  member,
  members,
  biddableProduct,
  bidLevels,
  isBidRange,
  quantityEnabled,
  saving,
  onSave,
}) => {
  const [memberId, setMemberId] = useState("");
  const [items, setItems] = useState<BidItemDraft[]>([]);
  const [enteredByAdmin, setEnteredByAdmin] = useState(true);

  // The form is reset when the modal opens; the values of the opening render
  // are the initial ones, so no reload can overwrite an open form.
  useEffect(() => {
    if (!show) return;
    setMemberId(member.memberId);
    setItems(
      editingBid
        ? bidToDraftItems(editingBid, isBidRange)
        : emptyBidItems(biddableProduct, bidLevels),
    );
    setEnteredByAdmin(editingBid ? !!editingBid.enteredByAdmin : true);
  }, [show]);

  const memberName = editingBid
    ? member.memberName
    : (members.find((entry) => entry.memberId === memberId)?.memberName ?? "");

  const updateBidItem = (index: number, patch: Partial<BidItemDraft>) => {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  };

  const removeBidItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const saveBid = () => {
    const payloadItems: BidItemPayload[] = items.map((item) => ({
      roundProductTypeId: item.roundProductTypeId,
      productId: item.productId,
      quantity: item.quantity,
      amount1: item.amount1 ?? null,
      amount2: item.amount2 ?? null,
      amount3: isBidRange ? null : (item.amount3 ?? null),
    }));
    onSave({
      memberId,
      items: payloadItems,
      enteredByAdmin,
    });
  };

  return (
    <Modal show={show} onHide={onHide} centered={true} size="lg">
      <Modal.Header closeButton>
        <h5 className="mb-0">
          {editingBid ? "Gebot bearbeiten" : "Gebot erfassen"}
          {memberName ? ` – ${memberName}` : ""}
        </h5>
      </Modal.Header>
      <Modal.Body>
        <Form>
          {!editingBid && (
            <Form.Group className="mb-2">
              <Form.Label>{"Mitglied"}</Form.Label>
              <Form.Select
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                required
              >
                <option value={""}>–</option>
                {members
                  .filter((entry) => !entry.hasBid)
                  .map((entry) => (
                    <option key={entry.memberId} value={entry.memberId}>
                      {entry.memberName}
                    </option>
                  ))}
              </Form.Select>
            </Form.Group>
          )}
          {items.length === 0 ? (
            <p className="text-muted">
              {"Keine bietbaren Produkte für diese Runde."}
            </p>
          ) : (
            items.map((item, index) => {
              return (
                <div key={index} className={"border rounded p-3 mb-3"}>
                  <div className="row">
                    <Form.Group className={"col-md-4 mb-2"}>
                      <Form.Label>{"Ernteanteil"}</Form.Label>
                      <div>{biddableProduct?.productTypeName}</div>
                    </Form.Group>
                    <Form.Group className={"col-md-3 mb-2"}>
                      <Form.Label>{"Variante"}</Form.Label>
                      <Form.Select
                        value={item.productId}
                        onChange={(event) =>
                          updateBidItem(index, {
                            productId: event.target.value,
                          })
                        }
                      >
                        {(biddableProduct?.products ?? []).map((product) => (
                          <option key={product.id} value={product.id}>
                            {product.name}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                    {quantityEnabled && (
                      <Form.Group className={"col-md-2 mb-2"}>
                        <Form.Label>{"Anteile"}</Form.Label>
                        <Form.Control
                          type="number"
                          min={1}
                          value={item.quantity}
                          onChange={(event) =>
                            updateBidItem(index, {
                              quantity: parseInt(event.target.value),
                            })
                          }
                        />
                      </Form.Group>
                    )}
                    {isBidRange
                      ? BID_RANGE_LEVELS.map((level) => (
                          <Form.Group
                            className={"col-md-4 mb-2"}
                            key={level.key}
                          >
                            <Form.Label className={level.textClass}>
                              <span
                                className={
                                  "d-inline-block rounded-circle me-2 " +
                                  level.dotClass
                                }
                                style={{ width: "0.7rem", height: "0.7rem" }}
                              />
                              {getBidRangeDefaultLabel(level)}
                            </Form.Label>
                            <Form.Control
                              type="number"
                              step="any"
                              min={0}
                              className={`${level.borderClass} border-2 ${level.bgClass}`}
                              value={item[level.key] ?? ""}
                              onChange={(event) =>
                                updateBidItem(index, {
                                  [level.key]: event.target.value,
                                } as Partial<BidItemDraft>)
                              }
                            />
                          </Form.Group>
                        ))
                      : Array.from(
                          { length: bidLevels },
                          (_, i) => (i + 1) as 1 | 2 | 3,
                        ).map((level) => {
                          const key = `amount${level}` as
                            "amount1" | "amount2" | "amount3";
                          return (
                            <Form.Group className={"col-md-3 mb-2"} key={level}>
                              <Form.Label>
                                {bidLevels === 1
                                  ? "Betrag €/Monat"
                                  : interpolate("Gebot {level} €/Monat", {
                                      level,
                                    })}
                              </Form.Label>
                              <Form.Control
                                type="number"
                                step="any"
                                min={0}
                                value={item[key] ?? ""}
                                onChange={(event) =>
                                  updateBidItem(index, {
                                    [key]: event.target.value,
                                  } as Partial<BidItemDraft>)
                                }
                              />
                            </Form.Group>
                          );
                        })}
                  </div>
                  {items.length > 1 && (
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => removeBidItem(index)}
                    >
                      {"Entfernen"}
                    </Button>
                  )}
                </div>
              );
            })
          )}
          <Form.Group className={"mt-3"}>
            <Form.Check
              type="checkbox"
              label={"von Admin erfasst"}
              checked={enteredByAdmin}
              onChange={(event) => setEnteredByAdmin(event.target.checked)}
            />
          </Form.Group>
          {editingBid && editingBid.adminConfirmed && (
            <div className={"mt-2"}>
              <span className={"text-success me-1"}>{"✓"}</span>
              {"Admin-bestätigt"}
            </div>
          )}
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="primary" onClick={saveBid} disabled={saving}>
          {saving ? "Speichert…" : "Speichern"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default BidEditModal;
