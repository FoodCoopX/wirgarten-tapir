import { useEffect, useMemo, useRef, useState } from "react";

import { BiddingRoundsApi } from "../../api-client/apis/BiddingRoundsApi.ts";
import type { ContractRow } from "../../api-client/models/ContractRow.ts";
import type { CreateContractsError } from "../../api-client/models/CreateContractsError.ts";
import type { RoundResultsResponse } from "../../api-client/models/RoundResultsResponse.ts";
import { useApi } from "../../hooks/useApi.ts";
import type { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import type { CoverageTarget } from "../types.ts";
import type { MemberWithBid } from "../utils/financingProjection.ts";
import {
  buildUpliftedReachedByPosition,
  computeFinancingProjection,
  findTargetCoveragePosition,
} from "../utils/financingProjection.ts";
import { computeTwelveMonthProjection } from "../utils/twelveMonthProjection.ts";
import { useBidEditor } from "./useBidEditor.ts";
import { useContractCreation } from "./useContractCreation.ts";

function getRoundIdFromPath(): string {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const adminIndex = parts.indexOf("admin");
  return parts[adminIndex + 1];
}

export function useBiddingRoundResults(csrfToken: string) {
  const api = useApi(BiddingRoundsApi, csrfToken);
  const [roundId] = useState(getRoundIdFromPath());

  const [data, setData] = useState<RoundResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const skipSliderLoadRef = useRef(false);
  const [includeAutoRenewed, setIncludeAutoRenewed] = useState(true);
  const [bidRangePosition, setBidRangePosition] = useState(50);
  const [newMembersPerMonth, setNewMembersPerMonth] = useState(2);
  const [surchargePercent, setSurchargePercent] = useState(0);
  const [surchargeOnBids, setSurchargeOnBids] = useState(true);
  const [surchargeOnAverage, setSurchargeOnAverage] = useState(true);
  const [debouncedBidRangePosition, setDebouncedBidRangePosition] =
    useState(50);
  const [bidLevels, setBidLevels] = useState(1);
  const [recommendedLevel, setRecommendedLevel] = useState(1);
  const [positionInitialized, setPositionInitialized] = useState(false);
  const [filter, setFilter] = useState("active_in_contract_period");
  const [sort, setSort] = useState("name");
  const [selectedBidIds, setSelectedBidIds] = useState<string[]>([]);
  const [selectedAutoRenewedMemberIds, setSelectedAutoRenewedMemberIds] =
    useState<string[]>([]);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [errorReport, setErrorReport] = useState<CreateContractsError[]>([]);
  const [averageBidLocked, setAverageBidLocked] = useState(false);
  const [contractsCreatedAt, setContractsCreatedAt] = useState<string | null>(
    null,
  );
  const [contracts, setContracts] = useState<ContractRow[]>([]);
  const [createAutoRenewed, setCreateAutoRenewed] = useState(false);
  const [showProjection, setShowProjection] = useState(false);

  const displayName: string = data?.displayName ?? "Beitragsrunde";

  const setPositionWithoutReload = (position: number) => {
    if (position !== debouncedBidRangePosition) {
      skipSliderLoadRef.current = true;
    }
    setBidRangePosition(position);
    setDebouncedBidRangePosition(position);
  };

  const loadResults = (autoJump = false) => {
    setLoading(true);
    api
      .biddingRoundsApiResultsRetrieve({
        roundId,
        includeAutoRenewed,
        bidRangePosition: positionInitialized
          ? debouncedBidRangePosition
          : undefined,
        filter,
        sort,
      })
      .then((response) => {
        setData(response);
        setBidLevels(response.bidLevels ?? 1);
        setRecommendedLevel(response.recommendedLevel ?? 1);
        setContractsCreatedAt(
          response.contractsCreatedAt
            ? String(response.contractsCreatedAt)
            : null,
        );
        setContracts(response.contracts ?? []);
        const locked = response.averageBidLockedAt != null;
        setAverageBidLocked(locked);
        if (locked) {
          setSurchargePercent(Number(response.lockedSurchargePercent ?? 0));
          setSurchargeOnBids(response.lockedSurchargeOnBids === true);
          setSurchargeOnAverage(response.lockedSurchargeOnAverage === true);
          const lockedPosition = Number(
            response.lockedBidRangePosition ?? response.bidRangePosition ?? 50,
          );
          setPositionWithoutReload(lockedPosition);
          setPositionInitialized(true);
        } else if (!positionInitialized) {
          const initialPosition = Number(response.bidRangePosition ?? 50);
          setPositionWithoutReload(initialPosition);
          setPositionInitialized(true);
        }
        if (autoJump && !locked) {
          const responseBids = response.bids ?? response.resultsTable.members;
          const responseIsBidRange = response.biddingProcedure === "bid_range";
          const responseBidReachedByPosition = surchargeOnBids
            ? buildUpliftedReachedByPosition(
                responseBids,
                1 + surchargePercent / 100,
                true,
                responseIsBidRange,
              )
            : undefined;
          const target = findTargetCoveragePosition(
            response.financingProjection,
            includeAutoRenewed,
            {
              surchargeOnBids,
              surchargeOnAverage,
              surchargeFactor: 1 + surchargePercent / 100,
              members: responseBids,
              isBidRange: responseIsBidRange,
              bidLevels: response.bidLevels,
              bidReachedByPosition: responseBidReachedByPosition,
            },
          );
          setPositionWithoutReload(target.position);
          setPositionInitialized(true);
        }
      })
      .catch((e) =>
        handleRequestError(
          e,
          "Auswertung konnte nicht geladen werden.",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const timeout = setTimeout(
      () => setDebouncedBidRangePosition(bidRangePosition),
      150,
    );
    return () => clearTimeout(timeout);
  }, [bidRangePosition]);

  useEffect(() => {
    loadResults(true);
  }, []);

  useEffect(() => {
    if (!positionInitialized) return;
    loadResults(true);
  }, [includeAutoRenewed]);

  useEffect(() => {
    if (!positionInitialized) return;
    if (skipSliderLoadRef.current) {
      skipSliderLoadRef.current = false;
      return;
    }
    loadResults(false);
  }, [debouncedBidRangePosition, filter, sort]);

  const contractCreation = useContractCreation({
    api,
    roundId,
    selectedBidIds,
    selectedAutoRenewedMemberIds,
    createAutoRenewed,
    setCreateAutoRenewed,
    setResultMessage,
    setErrorReport,
    setToastDatas,
    loadResults,
  });

  const bidEditor = useBidEditor({
    api,
    roundId,
    setResultMessage,
    setToastDatas,
    loadResults,
  });

  const toggleBid = (bidId: string | null) => {
    if (!bidId) return;
    setSelectedBidIds((prev) =>
      prev.includes(bidId)
        ? prev.filter((id) => id !== bidId)
        : [...prev, bidId],
    );
  };

  const toggleAutoRenewedMember = (memberId: string) => {
    setSelectedAutoRenewedMemberIds((prev) => {
      const selected = prev.includes(memberId);
      if (!selected) {
        setCreateAutoRenewed(true);
      }
      return selected
        ? prev.filter((id) => id !== memberId)
        : [...prev, memberId];
    });
  };

  const toggleAllBids = () => {
    const roundMembers = data?.resultsTable.members ?? [];
    const displayedBidIds = roundMembers
      .map((entry) => entry.bid?.id)
      .filter((id): id is string => Boolean(id));
    const displayedAutoRenewedIds = roundMembers
      .filter((entry) => !entry.hasBid && entry.isAutoRenewed)
      .map((entry) => entry.memberId);
    const allSelected =
      (displayedBidIds.length > 0 || displayedAutoRenewedIds.length > 0) &&
      displayedBidIds.every((id) => selectedBidIds.includes(id)) &&
      displayedAutoRenewedIds.every((id) =>
        selectedAutoRenewedMemberIds.includes(id),
      );
    setSelectedBidIds(allSelected ? [] : displayedBidIds);
    setSelectedAutoRenewedMemberIds(allSelected ? [] : displayedAutoRenewedIds);
    if (!allSelected && displayedAutoRenewedIds.length > 0) {
      setCreateAutoRenewed(true);
    }
  };

  const confirmBids = async () => {
    try {
      await api.biddingRoundsApiConfirmBidsCreate({
        roundId,
        confirmBidsRequest: { bidIds: selectedBidIds },
      });
      setResultMessage("Gebote bestätigt.");
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Gebote konnten nicht bestätigt werden.",
        setToastDatas,
      );
    }
  };

  const confirmAllBids = async () => {
    try {
      await api.biddingRoundsApiConfirmBidsCreate({
        roundId,
        confirmBidsRequest: {},
      });
      setResultMessage("Alle bestätigt.");
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Gebote konnten nicht bestätigt werden.",
        setToastDatas,
      );
    }
  };

  const lockAverageBid = async () => {
    try {
      await api.biddingRoundsApiLockAverageBidCreate({
        roundId,
        lockAverageBidRequest: {
          position: bidRangePosition,
          surchargePercent,
          surchargeOnBids,
          surchargeOnAverage,
        },
      });
      setResultMessage("Durchschnittsgebot gesperrt.");
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Das Durchschnittsgebot konnte nicht gesperrt werden.",
        setToastDatas,
      );
    }
  };

  const unlockAverageBid = async () => {
    if (
      !window.confirm(
        "Sperre des Durchschnittsgebots aufheben? Der gesperrte Wert wird verworfen und kann erneut gewählt werden.",
      )
    ) {
      return;
    }
    try {
      await api.biddingRoundsApiUnlockAverageBidCreate({ roundId });
      setResultMessage("Sperre des Durchschnittsgebots aufgehoben.");
      loadResults(true);
    } catch (e) {
      handleRequestError(
        e,
        "Die Sperre des Durchschnittsgebots konnte nicht aufgehoben werden.",
        setToastDatas,
      );
    }
  };

  const members = useMemo(
    () => data?.resultsTable.members ?? [],
    [data?.resultsTable.members],
  );
  const allBids = useMemo<MemberWithBid[]>(
    () => data?.bids ?? members,
    [data?.bids, members],
  );
  const pickupFill = useMemo(
    () => data?.resultsTable.pickupLocations ?? [],
    [data?.resultsTable.pickupLocations],
  );
  const displayedBidIds = useMemo(
    () => members.flatMap((entry) => (entry.bid ? [entry.bid.id] : [])),
    [members],
  );
  const displayedAutoRenewedMemberIds = useMemo(
    () =>
      members
        .filter((entry) => !entry.hasBid && entry.isAutoRenewed)
        .map((entry) => entry.memberId),
    [members],
  );
  const allDisplayedSelected = useMemo(
    () =>
      (displayedBidIds.length > 0 ||
        displayedAutoRenewedMemberIds.length > 0) &&
      displayedBidIds.every((id) => selectedBidIds.includes(id)) &&
      displayedAutoRenewedMemberIds.every((id) =>
        selectedAutoRenewedMemberIds.includes(id),
      ),
    [
      displayedBidIds,
      displayedAutoRenewedMemberIds,
      selectedBidIds,
      selectedAutoRenewedMemberIds,
    ],
  );
  const selectedBidsConfirmed = useMemo(
    () =>
      selectedBidIds.every((id) => {
        const entry = members.find((m) => m.bid?.id === id);
        return entry?.bid?.adminConfirmed != null;
      }),
    [members, selectedBidIds],
  );
  const hasContractSelection =
    selectedBidIds.length > 0 || selectedAutoRenewedMemberIds.length > 0;
  const canOpenContractsModal = averageBidLocked && hasContractSelection;

  const financingProjection = data?.financingProjection;
  const isBidRange = data?.biddingProcedure === "bid_range";
  const membershipIncludedInProductType =
    financingProjection?.membershipIncludedInProductType === true;
  const membershipFeesApply =
    Number(financingProjection?.membershipPerYear ?? 0) > 0;
  const surchargeFactor = 1 + surchargePercent / 100;
  const upliftedReachedByPosition = useMemo(
    () =>
      surchargeOnBids
        ? buildUpliftedReachedByPosition(
            allBids,
            surchargeFactor,
            true,
            isBidRange,
          )
        : [],
    [allBids, surchargeFactor, surchargeOnBids, isBidRange],
  );

  const dynamicProjection = useMemo(
    () =>
      financingProjection
        ? computeFinancingProjection(
            financingProjection,
            bidRangePosition,
            includeAutoRenewed,
            {
              surchargeOnBids,
              surchargeOnAverage,
              surchargeFactor,
              members: allBids,
              isBidRange,
              bidReached: surchargeOnBids
                ? upliftedReachedByPosition[Math.round(bidRangePosition)]
                : undefined,
            },
          )
        : null,
    [
      financingProjection,
      bidRangePosition,
      includeAutoRenewed,
      surchargeOnBids,
      surchargeOnAverage,
      surchargeFactor,
      allBids,
      isBidRange,
      upliftedReachedByPosition,
    ],
  );

  const coverageTarget = useMemo<CoverageTarget | null>(
    () =>
      financingProjection
        ? findTargetCoveragePosition(financingProjection, includeAutoRenewed, {
            surchargeOnBids,
            surchargeOnAverage,
            surchargeFactor,
            members: allBids,
            isBidRange,
            bidLevels,
            bidReachedByPosition: surchargeOnBids
              ? upliftedReachedByPosition
              : undefined,
          })
        : null,
    [
      financingProjection,
      includeAutoRenewed,
      surchargeOnBids,
      surchargeOnAverage,
      surchargeFactor,
      allBids,
      isBidRange,
      bidLevels,
      upliftedReachedByPosition,
    ],
  );

  const goToCoverageTarget = () => {
    if (!coverageTarget) return;
    setPositionWithoutReload(coverageTarget.position);
  };

  const twelveMonthProjection = useMemo(
    () =>
      showProjection && dynamicProjection && financingProjection
        ? computeTwelveMonthProjection({
            financingProjection,
            dynamicProjection,
            includeAutoRenewed,
            surchargeOnBids,
            surchargeOnAverage,
            surchargeFactor,
            members: allBids,
            isBidRange,
            bidLevels,
            bidRangePosition,
            newMembersPerMonth,
            bidReachedByPosition: upliftedReachedByPosition,
          })
        : null,
    [
      showProjection,
      dynamicProjection,
      financingProjection,
      bidRangePosition,
      includeAutoRenewed,
      surchargeOnBids,
      surchargeOnAverage,
      surchargeFactor,
      allBids,
      isBidRange,
      bidLevels,
      newMembersPerMonth,
      upliftedReachedByPosition,
    ],
  );

  return {
    roundId,
    data,
    loading,
    toastDatas,
    setToastDatas,
    displayName,
    resultMessage,
    errorReport,
    filter,
    setFilter,
    sort,
    setSort,
    members,
    pickupFill,
    biddableProduct: data?.biddableProduct ?? null,
    bidOptions: data?.bidOptions ?? {
      quantityEnabled: false,
      carouselEnabled: false,
    },
    bidLevels,
    recommendedLevel,
    includeAutoRenewed,
    setIncludeAutoRenewed,
    isBidRange,
    bidRangePosition,
    setBidRangePosition,
    surchargePercent,
    setSurchargePercent,
    surchargeOnBids,
    setSurchargeOnBids,
    surchargeOnAverage,
    setSurchargeOnAverage,
    surchargeFactor,
    membershipIncludedInProductType,
    membershipFeesApply,
    financingProjection,
    dynamicProjection,
    coverageTarget,
    goToCoverageTarget,
    twelveMonthProjection,
    showProjection,
    setShowProjection,
    newMembersPerMonth,
    setNewMembersPerMonth,
    averageBidLocked,
    contractsCreatedAt,
    contracts,
    selectedBidIds,
    selectedAutoRenewedMemberIds,
    allDisplayedSelected,
    toggleBid,
    toggleAutoRenewedMember,
    toggleAllBids,
    confirmBids,
    confirmAllBids,
    selectedBidsConfirmed,
    hasContractSelection,
    canOpenContractsModal,
    createAutoRenewed,
    setCreateAutoRenewed,
    lockAverageBid,
    unlockAverageBid,
    ...contractCreation,
    ...bidEditor,
  };
}
