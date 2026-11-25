import type { Dispatch, SetStateAction } from "react";
import { useState } from "react";

import type { BiddingRoundsApi } from "../../api-client/apis/BiddingRoundsApi.ts";
import type { Bid } from "../../api-client/models/Bid.ts";
import type { BidAdminCreateRequest } from "../../api-client/models/BidAdminCreateRequest.ts";
import type { PatchedBidAdminRequest } from "../../api-client/models/PatchedBidAdminRequest.ts";
import type { ResultsTableMember } from "../../api-client/models/ResultsTableMember.ts";
import type { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { interpolate } from "../../utils/interpolate.ts";
import type { BidFormPayload, BidMemberSelection } from "../types.ts";

interface UseBidEditorParams {
  api: BiddingRoundsApi;
  roundId: string;
  setResultMessage: (message: string | null) => void;
  setToastDatas: Dispatch<SetStateAction<ToastData[]>>;
  loadResults: (autoJump?: boolean) => void;
}

export function useBidEditor({
  api,
  roundId,
  setResultMessage,
  setToastDatas,
  loadResults,
}: UseBidEditorParams) {
  const [showBidModal, setShowBidModal] = useState(false);
  const [editingBid, setEditingBid] = useState<Bid | null>(null);
  const [bidModalMember, setBidModalMember] = useState<BidMemberSelection>({
    memberId: "",
    memberName: "",
  });
  const [savingBid, setSavingBid] = useState(false);

  const openCreateBidModal = (member?: BidMemberSelection) => {
    setEditingBid(null);
    setBidModalMember(member ?? { memberId: "", memberName: "" });
    setShowBidModal(true);
  };

  const openEditBidModal = (entry: ResultsTableMember) => {
    if (!entry.bid) return;
    setEditingBid(entry.bid);
    setBidModalMember({
      memberId: entry.memberId,
      memberName: entry.memberName,
    });
    setShowBidModal(true);
  };

  const closeBidModal = () => setShowBidModal(false);

  const saveBid = async (payload: BidFormPayload) => {
    setSavingBid(true);
    try {
      if (editingBid) {
        const request: PatchedBidAdminRequest = {
          productId: payload.productId,
          quantity: payload.quantity,
          amount1: payload.amount1 ?? null,
          amount2: payload.amount2 ?? null,
          amount3: payload.amount3 ?? null,
          enteredByAdmin: payload.enteredByAdmin,
        };
        await api.biddingRoundsApiBidsPartialUpdate({
          roundId,
          bidId: editingBid.id,
          patchedBidAdminRequest: request,
        });
      } else {
        const request: BidAdminCreateRequest = {
          memberId: payload.memberId,
          productId: payload.productId,
          quantity: payload.quantity,
          amount1: payload.amount1 ?? null,
          amount2: payload.amount2 ?? null,
          amount3: payload.amount3 ?? null,
          enteredByAdmin: payload.enteredByAdmin,
        };
        await api.biddingRoundsApiBidsCreate({
          roundId,
          bidAdminCreateRequest: request,
        });
      }
      setShowBidModal(false);
      setEditingBid(null);
      setResultMessage(editingBid ? "Gebot aktualisiert." : "Gebot erfasst.");
      loadResults(true);
    } catch (e) {
      handleRequestError(
        e,
        "Gebot konnte nicht gespeichert werden.",
        setToastDatas,
      );
    } finally {
      setSavingBid(false);
    }
  };

  const deleteBid = async (entry: ResultsTableMember) => {
    const bid = entry.bid;
    if (!bid) return;
    if (
      !window.confirm(
        interpolate('Gebot von "{name}" wirklich löschen?', {
          name: entry.memberName,
        }),
      )
    ) {
      return;
    }
    try {
      await api.biddingRoundsApiBidsDestroy({ roundId, bidId: bid.id });
      setResultMessage("Gebot gelöscht.");
      loadResults(true);
    } catch (e) {
      handleRequestError(
        e,
        "Gebot konnte nicht gelöscht werden.",
        setToastDatas,
      );
    }
  };

  return {
    showBidModal,
    editingBid,
    bidModalMember,
    savingBid,
    openCreateBidModal,
    openEditBidModal,
    closeBidModal,
    saveBid,
    deleteBid,
  };
}
