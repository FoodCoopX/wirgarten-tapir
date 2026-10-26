import {
  BarElement,
  CategoryScale,
  ChartData,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Collapse,
  Container,
  Form,
  Modal,
  ProgressBar,
  Spinner,
  Table,
} from "react-bootstrap";
import { Bar } from "react-chartjs-2";

import { BiddingRoundsApi } from "../api-client/apis/BiddingRoundsApi.ts";
import { applyDisplayName } from "../bidding_round/utils/applyDisplayName.ts";
import {
  getTrafficLightDefaultLabel,
  TRAFFIC_LIGHT_LEVELS,
} from "../bidding_round/utils/trafficLightLevels.ts";
import DeckungAuslastungBars from "../components/DeckungAuslastungBars.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { interpolate } from "../utils/interpolate.ts";
import {
  coverageVariant,
  formatEuro,
  formatNumber,
  formatPercent,
  interpolateLevel,
  levelFromPosition,
} from "../utils/resultsFormat.ts";

interface BiddingRoundResultsProps {
  csrfToken: string;
}

interface BidItemDraft {
  roundProductId: string;
  productId: string;
  quantity: number;
  amount1?: string | null;
  amount2?: string | null;
  amount3?: string | null;
}

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Filler,
  Title,
  Tooltip,
  Legend,
);

function getRoundIdFromPath(): string {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const adminIndex = parts.indexOf("admin");
  return parts[adminIndex + 1];
}

function itemLevels(item: any) {
  const a1 = item.amount1 != null ? Number(item.amount1) : null;
  const a2 = item.amount2 != null ? Number(item.amount2) : null;
  const a3 = item.amount3 != null ? Number(item.amount3) : null;
  const base = a2 ?? a1 ?? a3 ?? 0;
  return {
    a1,
    a2,
    a3,
    base,
    green: a1 ?? base,
    yellow: a2 ?? base,
    red: a3 ?? base,
  };
}

// Amount of a bid item at a position on the 0/50/100 axis. Level 1/2/3 are
// stored in amount_1/2/3 (traffic light: green/wish, yellow/satisfied, red/pain threshold). Missing levels fall back to
// the base level, so a simple round with N levels yields exact level values at the
// positions 0/50/100.
function itemAmountAtPosition(item: any, position: number): number {
  const levels = itemLevels(item);
  return interpolateLevel(levels.green, levels.yellow, levels.red, position);
}

// Effective amount at the chosen level. For the traffic light the optional surcharge is
// capped at the pain threshold (red); the simple procedure has a single amount and
// no cap.
function effectiveAmount(
  green: number,
  yellow: number,
  red: number,
  position: number,
  applySurcharge: boolean,
  factor: number,
  isTrafficLight: boolean,
): number {
  const base = interpolateLevel(green, yellow, red, position);
  if (!applySurcharge) {
    return base;
  }
  return isTrafficLight ? Math.min(base * factor, red) : base * factor;
}

// Illustrative example bids (green / yellow / red) used in the expandable example.
const EXAMPLE_BIDS = [
  { label: "Gebot A", green: 60, yellow: 80, red: 100 },
  { label: "Gebot B", green: 70, yellow: 85, red: 105 },
  { label: "Gebot C", green: 50, yellow: 75, red: 95 },
];

// Apply the surcharge to the bids, never exceeding each bid's pain threshold (red).
function computeUpliftedBidReached(
  members: any[],
  position: number,
  factor: number,
  applyToBids: boolean,
  isTrafficLight: boolean,
): number {
  let total = 0;
  for (const entry of members) {
    for (const item of entry.bid?.items ?? []) {
      const levels = itemLevels(item);
      const value = effectiveAmount(
        levels.green,
        levels.yellow,
        levels.red,
        position,
        applyToBids,
        factor,
        isTrafficLight,
      );
      total += value * item.quantity * 12;
    }
  }
  return total;
}

/**
 * Fair model: bidders pay their bid at the chosen solidarity level; everyone who
 * did not bid (auto-renewed members and members joining after the round) pays the
 * same dynamic average bid, derived so the target is covered at full capacity.
 * An optional surcharge can be applied to the bids and/or to the average to also
 * cover the gap of unallocated shares. For the traffic light the surcharge is capped at
 * the pain threshold (red); the simple procedure has a single amount and no cap.
 */
function computeFinancingProjection(
  projection: any,
  position: number,
  includeAutoRenewed: boolean,
  options: {
    surchargeOnBids?: boolean;
    surchargeOnAverage?: boolean;
    surchargeFactor?: number;
    members?: any[];
    isTrafficLight?: boolean;
  } = {},
) {
  const isTrafficLight = options.isTrafficLight ?? true;
  const levels = projection.levels;
  const baseBidReached = interpolateLevel(
    Number(levels.green.reachedPerYear),
    Number(levels.yellow.reachedPerYear),
    Number(levels.red.reachedPerYear),
    position,
  );

  const factor = options.surchargeFactor ?? 1;
  const bidReached =
    options.surchargeOnBids && options.members
      ? computeUpliftedBidReached(
          options.members,
          position,
          factor,
          true,
          isTrafficLight,
        )
      : baseBidReached;

  const bidShares = Number(projection.bidShares);
  const bidderAveragePerMonth =
    bidShares > 0 ? bidReached / (bidShares * 12) : 0;

  const target = Number(projection.targetPerYear);
  const otherFixed =
    Number(projection.membershipPerYear ?? 0) +
    Number(projection.deliveryChargePerYear ?? 0);
  const autoShares = Number(projection.autoShares ?? 0);
  const remainingShares = Number(projection.remainingShares ?? 0);
  const payerShares = includeAutoRenewed
    ? autoShares + remainingShares
    : remainingShares;

  // Base average derived so the target is covered at full capacity (no surcharge).
  // With the non-bidder floor, non-bidders pay at least the bidders' average.
  const floorEnabled = projection.nonBiddersMinAverage === true;
  let baseAverage =
    payerShares > 0
      ? (target - otherFixed - baseBidReached) / (payerShares * 12)
      : 0;
  if (floorEnabled) {
    baseAverage = Math.max(baseAverage, bidderAveragePerMonth);
  }
  const redAverage = Number(levels.red.averagePerSharePerMonth);
  let averagePerSharePerMonth = options.surchargeOnAverage
    ? isTrafficLight
      ? Math.min(baseAverage * factor, redAverage)
      : baseAverage * factor
    : baseAverage;
  // The floor always holds, even after the surcharge cap.
  if (floorEnabled) {
    averagePerSharePerMonth = Math.max(
      averagePerSharePerMonth,
      bidderAveragePerMonth,
    );
  }

  const autoTotal = includeAutoRenewed
    ? autoShares * averagePerSharePerMonth * 12
    : 0;
  const latecomerTotal = remainingShares * averagePerSharePerMonth * 12;
  const total = bidReached + otherFixed + autoTotal + latecomerTotal;
  const coverage = target > 0 ? (total / target) * 100 : 0;

  // Contributions from the members already in the round (without latecomers).
  const currentTotal = bidReached + otherFixed + autoTotal;
  const currentCoverage = target > 0 ? (currentTotal / target) * 100 : 0;

  // Base model (without surcharge) and the surcharge share, so it can be shown
  // as its own line in the breakdown.
  const baseAutoTotal = includeAutoRenewed ? autoShares * baseAverage * 12 : 0;
  const baseLatecomerTotal = remainingShares * baseAverage * 12;
  const baseTotal =
    baseBidReached + otherFixed + baseAutoTotal + baseLatecomerTotal;
  const surchargeTotal = total - baseTotal;

  const capacityShares = Number(projection.capacityShares);
  const currentShares = bidShares + (includeAutoRenewed ? autoShares : 0);
  const utilization =
    capacityShares > 0 ? (currentShares / capacityShares) * 100 : 0;

  return {
    baseBidReached,
    bidReached,
    bidderAveragePerMonth,
    baseAverage,
    averagePerSharePerMonth,
    otherFixed,
    autoTotal,
    latecomerTotal,
    baseAutoTotal,
    baseLatecomerTotal,
    baseTotal,
    surchargeTotal,
    payerShares,
    total,
    currentTotal,
    currentCoverage,
    target,
    coverage,
    currentShares,
    capacityShares,
    utilization,
  };
}

const BiddingRoundResults: React.FC<BiddingRoundResultsProps> = ({
  csrfToken,
}) => {
  const api = useApi(BiddingRoundsApi, csrfToken);
  const [roundId] = useState(getRoundIdFromPath());

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [includeAutoRenewed, setIncludeAutoRenewed] = useState(true);
  const [trafficLightPosition, setTrafficLightPosition] = useState(50);
  const [newMembersPerMonth, setNewMembersPerMonth] = useState(2);
  const [surchargePercent, setSurchargePercent] = useState(0);
  const [surchargeOnBids, setSurchargeOnBids] = useState(true);
  const [surchargeOnAverage, setSurchargeOnAverage] = useState(true);
  const [debouncedTrafficLightPosition, setDebouncedTrafficLightPosition] =
    useState(50);
  const [bidLevels, setBidLevels] = useState(1);
  const [recommendedLevel, setRecommendedLevel] = useState(1);
  const [positionInitialized, setPositionInitialized] = useState(false);
  const [filter, setFilter] = useState("active_in_contract_period");
  const [sort, setSort] = useState("name");
  const [showEmails, setShowEmails] = useState(false);
  const [selectedBidIds, setSelectedBidIds] = useState<string[]>([]);
  const [selectedAutoRenewedMemberIds, setSelectedAutoRenewedMemberIds] =
    useState<string[]>([]);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [errorReport, setErrorReport] = useState<any[]>([]);
  const [averageBidLocked, setAverageBidLocked] = useState(false);
  const [contractsCreatedAt, setContractsCreatedAt] = useState<string | null>(
    null,
  );
  const [contracts, setContracts] = useState<any[]>([]);
  const [showContractsModal, setShowContractsModal] = useState(false);
  const [checkLoading, setCheckLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createAutoRenewed, setCreateAutoRenewed] = useState(false);
  const [checkMessage, setCheckMessage] = useState<string | null>(null);
  const [checkErrors, setCheckErrors] = useState<any[]>([]);

  const [showBidModal, setShowBidModal] = useState(false);
  const [showExample, setShowExample] = useState(false);
  const [showFormula, setShowFormula] = useState(false);
  const [showSurcharge, setShowSurcharge] = useState(false);
  const [showProjection, setShowProjection] = useState(false);
  const [editingBid, setEditingBid] = useState<any | null>(null);
  const [bidModalMemberName, setBidModalMemberName] = useState("");
  const [createMemberId, setCreateMemberId] = useState("");
  const [bidItems, setBidItems] = useState<BidItemDraft[]>([]);
  const [bidPickupLocationId, setBidPickupLocationId] = useState("");
  const [bidAdminConfirmed, setBidAdminConfirmed] = useState(false);
  const [bidEnteredByAdmin, setBidEnteredByAdmin] = useState(true);
  const [savingBid, setSavingBid] = useState(false);
  const displayName: string = data?.displayName ?? "Beitragsrunde";

  const loadResults = () => {
    setLoading(true);
    api
      .biddingRoundsApiResultsRetrieve({
        roundId,
        includeAutoRenewed,
        trafficLightPosition: positionInitialized
          ? debouncedTrafficLightPosition
          : undefined,
        filter,
        sort,
      })
      .then((response: any) => {
        setData(response);
        setBidLevels(response?.bidLevels ?? 1);
        setRecommendedLevel(response?.recommendedLevel ?? 1);
        setContractsCreatedAt(response?.contractsCreatedAt ?? null);
        setContracts(response?.contracts ?? []);
        const locked = response?.averageBidLockedAt != null;
        setAverageBidLocked(locked);
        if (locked) {
          setSurchargePercent(Number(response?.lockedSurchargePercent ?? 0));
          setSurchargeOnBids(response?.lockedSurchargeOnBids === true);
          setSurchargeOnAverage(response?.lockedSurchargeOnAverage === true);
          const lockedPosition = Number(
            response?.lockedTrafficLightPosition ??
              response?.trafficLightPosition ??
              50,
          );
          setTrafficLightPosition(lockedPosition);
          setDebouncedTrafficLightPosition(lockedPosition);
          setPositionInitialized(true);
        } else if (!positionInitialized) {
          const initialPosition = Number(response?.trafficLightPosition ?? 50);
          setTrafficLightPosition(initialPosition);
          setDebouncedTrafficLightPosition(initialPosition);
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
      () => setDebouncedTrafficLightPosition(trafficLightPosition),
      150,
    );
    return () => clearTimeout(timeout);
  }, [trafficLightPosition]);

  useEffect(loadResults, [
    api,
    roundId,
    includeAutoRenewed,
    debouncedTrafficLightPosition,
    positionInitialized,
    filter,
    sort,
  ]);

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
    const roundMembers = data?.resultsTable?.members ?? [];
    const displayedBidIds = roundMembers
      .map((entry: any) => entry.bid?.id)
      .filter(Boolean) as string[];
    const displayedAutoRenewedIds = roundMembers
      .filter((entry: any) => !entry.hasBid && entry.isAutoRenewed)
      .map((entry: any) => entry.memberId) as string[];
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
      } as any);
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

  const runCheckContracts = async () => {
    setCheckLoading(true);
    setCheckMessage(null);
    try {
      const response = await api.biddingRoundsApiCheckContractsCreate({
        roundId,
        checkContractsRequest: { bidIds: selectedBidIds },
      } as any);
      const errors: any[] = (response as any)?.errors ?? [];
      setCheckErrors(errors);
      setCheckMessage(
        errors.length === 0
          ? "Aus allen ausgewählten Geboten können Verträge erzeugt werden."
          : interpolate(
              "Aus {count} Geboten können keine Verträge erzeugt werden.",
              { count: errors.length },
            ),
      );
    } catch (e) {
      handleRequestError(
        e,
        "Die Verträge konnten nicht geprüft werden.",
        setToastDatas,
      );
    } finally {
      setCheckLoading(false);
    }
  };

  const createContracts = async () => {
    setCreateLoading(true);
    try {
      const response = await api.biddingRoundsApiCreateContractsCreate({
        roundId,
        createContractsRequest: {
          bidIds: selectedBidIds,
          autoRenewedMemberIds: selectedAutoRenewedMemberIds,
          createAutoRenewedContracts: createAutoRenewed,
        } as any,
      } as any);
      const errors: any[] = (response as any)?.errors ?? [];
      setErrorReport(errors);
      setResultMessage(
        errors.length === 0
          ? "Verträge erzeugt."
          : interpolate("Verträge erzeugt mit {count} Fehlern.", {
              count: errors.length,
            }),
      );
      setShowContractsModal(false);
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Verträge konnten nicht erzeugt werden.",
        setToastDatas,
      );
    } finally {
      setCreateLoading(false);
    }
  };

  const openContractsModal = () => {
    setCreateAutoRenewed(selectedAutoRenewedMemberIds.length > 0);
    setCheckMessage(null);
    setCheckErrors([]);
    setShowContractsModal(true);
    runCheckContracts();
  };

  const lockAverageBid = async () => {
    try {
      await api.biddingRoundsApiLockAverageBidCreate({
        roundId,
        lockAverageBidRequest: {
          position: trafficLightPosition,
          surchargePercent,
          surchargeOnBids,
          surchargeOnAverage,
        },
      } as any);
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
      await api.biddingRoundsApiUnlockAverageBidCreate({ roundId } as any);
      setResultMessage("Sperre des Durchschnittsgebots aufgehoben.");
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Die Sperre des Durchschnittsgebots konnte nicht aufgehoben werden.",
        setToastDatas,
      );
    }
  };

  const deleteContracts = async () => {
    if (
      !window.confirm(
        "Alle von dieser Beitragsrunde erzeugten Verträge löschen? Die Preisanpassungen der Auto-Verlängerer werden ebenfalls zurückgesetzt.",
      )
    ) {
      return;
    }
    if (
      !window.confirm(
        "Sind Sie sicher? Dies kann nicht rückgängig gemacht werden. Alle erzeugten Verträge dieser Runde werden entfernt.",
      )
    ) {
      return;
    }
    try {
      await api.biddingRoundsApiDeleteContractsCreate({ roundId } as any);
      setResultMessage("Verträge gelöscht.");
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Die Verträge konnten nicht gelöscht werden.",
        setToastDatas,
      );
    }
  };

  const pickupLocations = data?.pickupLocations ?? [];
  const biddableProduct = data?.biddableProduct ?? null;
  const bidOptions = data?.bidOptions ?? {
    quantityEnabled: false,
    multiplePositionsEnabled: false,
  };
  const pickupLocationsEnabled = pickupLocations.length > 0;

  const defaultAmounts = (value: string | null): Partial<BidItemDraft> => {
    const trafficLight = data?.biddingProcedure === "traffic_light";
    const levels = trafficLight
      ? 3
      : Math.min(Math.max(data?.bidLevels ?? 1, 1), 3);
    return {
      amount1: value,
      ...(levels >= 2 ? { amount2: value } : {}),
      ...(levels >= 3 ? { amount3: value } : {}),
    };
  };

  const emptyBidItems = (): BidItemDraft[] => {
    const productType = biddableProduct;
    const product = productType?.products[0];
    if (!productType || !product) return [];
    return [
      {
        roundProductId: productType.id,
        productId: product.id,
        quantity: 1,
        ...defaultAmounts(""),
      },
    ];
  };

  const openCreateBidModal = () => {
    setEditingBid(null);
    setCreateMemberId("");
    setBidModalMemberName("");
    setBidAdminConfirmed(false);
    setBidEnteredByAdmin(true);
    setBidPickupLocationId("");
    setBidItems(emptyBidItems());
    setShowBidModal(true);
  };

  const openEditBidModal = (memberEntry: any) => {
    const bid = memberEntry.bid;
    if (!bid) return;
    setEditingBid(bid);
    setCreateMemberId(memberEntry.memberId);
    setBidModalMemberName(memberEntry.memberName);
    setBidAdminConfirmed(!!bid.adminConfirmed);
    setBidEnteredByAdmin(!!bid.enteredByAdmin);
    setBidPickupLocationId(bid.pickupLocationId ?? "");
    setBidItems(
      (bid.items ?? []).map((item: any) => ({
        roundProductId: item.roundProductId,
        productId: item.productId,
        quantity: item.quantity,
        amount1: item.amount1 ?? null,
        amount2: item.amount2 ?? null,
        amount3: item.amount3 ?? null,
      })),
    );
    setShowBidModal(true);
  };

  const updateBidItem = (index: number, patch: Partial<BidItemDraft>) => {
    setBidItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  };

  const removeBidItem = (index: number) => {
    setBidItems((prev) => prev.filter((_, i) => i !== index));
  };

  const saveBid = async () => {
    setSavingBid(true);
    const payload: any = {
      items: bidItems.map((item) => ({
        roundProductId: item.roundProductId,
        productId: item.productId,
        quantity: item.quantity,
        amount1: item.amount1 ?? null,
        amount2: item.amount2 ?? null,
        amount3: item.amount3 ?? null,
      })),
      pickupLocationId: bidPickupLocationId || null,
      enteredByAdmin: bidEnteredByAdmin,
      adminConfirmed: bidAdminConfirmed,
    };
    try {
      if (editingBid) {
        await api.biddingRoundsApiBidsPartialUpdate({
          roundId,
          bidId: editingBid.id,
          patchedBidAdminRequest: payload as any,
        } as any);
      } else {
        await api.biddingRoundsApiBidsCreate({
          roundId,
          bidAdminRequest: { ...payload, memberId: createMemberId } as any,
        } as any);
      }
      setShowBidModal(false);
      setEditingBid(null);
      setResultMessage(editingBid ? "Gebot aktualisiert." : "Gebot erfasst.");
      loadResults();
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

  const deleteBid = async (memberEntry: any) => {
    const bid = memberEntry.bid;
    if (!bid) return;
    if (
      !window.confirm(
        interpolate('Gebot von "{name}" wirklich löschen?', {
          name: memberEntry.memberName,
        }),
      )
    ) {
      return;
    }
    try {
      await api.biddingRoundsApiBidsDestroy({ roundId, bidId: bid.id });
      setResultMessage("Gebot gelöscht.");
      loadResults();
    } catch (e) {
      handleRequestError(
        e,
        "Gebot konnte nicht gelöscht werden.",
        setToastDatas,
      );
    }
  };

  if (loading && !data) {
    return (
      <>
        <Container className="d-flex justify-content-center mt-5">
          <Spinner animation="border" />
        </Container>
        <TapirToastContainer
          toastDatas={toastDatas}
          setToastDatas={setToastDatas}
        />
      </>
    );
  }

  const members = data?.resultsTable?.members ?? [];
  const pickupFill = data?.resultsTable?.pickupLocations ?? [];
  const hasBids = members.some((m: any) => m.hasBid);
  const displayedBidIds = members
    .map((entry: any) => entry.bid?.id)
    .filter(Boolean) as string[];
  const displayedAutoRenewedMemberIds = members
    .filter((entry: any) => !entry.hasBid && entry.isAutoRenewed)
    .map((entry: any) => entry.memberId) as string[];
  const allDisplayedAutoRenewedSelected =
    displayedAutoRenewedMemberIds.length === 0 ||
    displayedAutoRenewedMemberIds.every((id) =>
      selectedAutoRenewedMemberIds.includes(id),
    );
  const allDisplayedSelected =
    (displayedBidIds.length > 0 || displayedAutoRenewedMemberIds.length > 0) &&
    displayedBidIds.every((id) => selectedBidIds.includes(id)) &&
    displayedAutoRenewedMemberIds.every((id) =>
      selectedAutoRenewedMemberIds.includes(id),
    );
  const selectedBidsConfirmed = selectedBidIds.every((id) => {
    const entry = members.find((m: any) => m.bid?.id === id);
    return entry?.bid?.adminConfirmed != null;
  });
  const hasContractSelection =
    selectedBidIds.length > 0 || selectedAutoRenewedMemberIds.length > 0;
  const canCreateContracts =
    averageBidLocked && hasContractSelection && selectedBidsConfirmed;
  const isSolidarityRound = true;

  const financingProjection = data?.financingProjection;
  const isTrafficLight = data?.biddingProcedure === "traffic_light";
  const nonBiddersMinAverage =
    financingProjection?.nonBiddersMinAverage === true;
  const membershipIncludedInProductType =
    financingProjection?.membershipIncludedInProductType === true;
  const membershipFeesApply =
    Number(financingProjection?.membershipPerYear ?? 0) > 0;
  const surchargeFactor = 1 + surchargePercent / 100;
  const dynamicProjection = financingProjection
    ? computeFinancingProjection(
        financingProjection,
        trafficLightPosition,
        includeAutoRenewed,
        {
          surchargeOnBids,
          surchargeOnAverage,
          surchargeFactor,
          members,
          isTrafficLight,
        },
      )
    : null;

  // 12-month projection: the admin estimates how many new members join per month
  // (slider). The chart combines the member growth (bars, cumulative) with the
  // cumulative balance (lines) for each bid level and the current dynamic level.
  const twelveMonthProjection = dynamicProjection
    ? (() => {
        const months = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        const openShares = Number(financingProjection.remainingShares ?? 0);
        const monthlyTarget = dynamicProjection.target / 12;

        const joinedBy = (month: number) =>
          Math.min(newMembersPerMonth * month, openShares);
        const membersData = months.map((month) => joinedBy(month));

        const saldoFor = (projectionAtLevel: any) => {
          const committedMonthly =
            (projectionAtLevel.bidReached +
              projectionAtLevel.autoTotal +
              projectionAtLevel.otherFixed) /
            12;
          const perShareMonthly = projectionAtLevel.averagePerSharePerMonth;
          let revenueCumulative = 0;
          let costsCumulative = 0;
          return months.map((month) => {
            if (month === 0) {
              return 0;
            }
            revenueCumulative +=
              committedMonthly + joinedBy(month) * perShareMonthly;
            costsCumulative += monthlyTarget;
            return revenueCumulative - costsCumulative;
          });
        };

        const projectionAt = (position: number) =>
          computeFinancingProjection(
            financingProjection,
            position,
            includeAutoRenewed,
            {
              surchargeOnBids,
              surchargeOnAverage,
              surchargeFactor,
              members,
              isTrafficLight,
            },
          );

        const currentLabel = isTrafficLight
          ? interpolate("Saldo dynamisch (Niveau {position})", {
              position: trafficLightPosition,
            })
          : interpolate("Saldo Stufe {level}", {
              level: levelFromPosition(trafficLightPosition, bidLevels),
            });
        const series: { label: string; color: string; data: number[] }[] = [];
        if (isTrafficLight) {
          series.push(
            {
              label: "Saldo Grün (Wunsch)",
              color: "#198754",
              data: saldoFor(projectionAt(0)),
            },
            {
              label: "Saldo Gelb (Zufrieden)",
              color: "#ffc107",
              data: saldoFor(projectionAt(50)),
            },
            {
              label: "Saldo Rot (Schmerzgrenze)",
              color: "#dc3545",
              data: saldoFor(projectionAt(100)),
            },
          );
        } else {
          const palette = ["#198754", "#ffc107", "#dc3545"];
          for (let level = 1; level <= bidLevels; level++) {
            series.push({
              label: interpolate("Saldo Gebot {level}", { level }),
              color: palette[level - 1] ?? "#0d6efd",
              data: saldoFor(projectionAt((level - 1) * 50)),
            });
          }
        }
        series.push({
          label: currentLabel,
          color: "#fd7e14",
          data: saldoFor(dynamicProjection),
        });

        const currentSaldo = saldoFor(dynamicProjection);
        let breakEvenMonth: number | null = null;
        for (let month = 1; month <= 12; month++) {
          if (currentSaldo[month] >= -0.01) {
            breakEvenMonth = month;
            break;
          }
        }

        return {
          openShares,
          breakEvenMonth,
          saldoAfterTwelveMonths: currentSaldo[12],
          chartData: {
            labels: months.map((month) =>
              month === 0 ? "Start" : interpolate("Monat {month}", { month }),
            ),
            datasets: [
              {
                type: "bar",
                label: "Neue Mitglieder (kumuliert)",
                data: membersData,
                backgroundColor: "rgba(13,110,253,0.55)",
                yAxisID: "members",
              },
              ...series.map((entry) => ({
                type: "line" as const,
                label: entry.label,
                data: entry.data,
                borderColor: entry.color,
                backgroundColor: entry.color,
                borderWidth: entry.label === currentLabel ? 3 : 1.5,
                borderDash: entry.label === currentLabel ? undefined : [5, 3],
                tension: 0.2,
                pointRadius: 0,
                yAxisID: "saldo",
              })),
              {
                type: "line",
                label: "Break-even (0 €)",
                data: months.map(() => 0),
                borderColor: "#adb5bd",
                borderDash: [6, 4],
                pointRadius: 0,
                yAxisID: "saldo",
              },
            ],
          } as unknown as ChartData<"bar">,
        };
      })()
    : null;

  const pickupChartData: ChartData<"bar"> = {
    labels: pickupFill.map((entry: any) => entry.pickupLocationName),
    datasets: [
      {
        label: "Kapazität",
        data: pickupFill.map((entry: any) => Number(entry.capacity)),
        backgroundColor: "rgba(13, 110, 253, 0.6)",
      },
      {
        label: "Nachfrage",
        data: pickupFill.map((entry: any) => Number(entry.demand)),
        backgroundColor: "rgba(25, 135, 84, 0.6)",
      },
    ],
  };

  function renderMemberItems(bid: any): string {
    if (!bid) return "–";
    return (bid.items ?? [])
      .map(
        (item: any) =>
          `${item.productTypeName} (${item.productName}) ×${item.quantity}`,
      )
      .join(", ");
  }

  function renderContractItems(items: any[]): string {
    if (!items || items.length === 0) return "–";
    return items
      .map(
        (item: any) =>
          `${item.productTypeName} (${item.productName}) ×${item.quantity}`,
      )
      .join(", ");
  }

  function bidAmountForLevel(bid: any, level: 1 | 2 | 3) {
    if (!bid) return null;
    return (bid.items ?? []).reduce((sum: number, item: any) => {
      const levels = itemLevels(item);
      const amount =
        level === 1 ? levels.green : level === 2 ? levels.yellow : levels.red;
      return sum + amount * item.quantity;
    }, 0);
  }

  function bidAmountAtPosition(
    bid: any,
    position: number,
    applySurcharge: boolean,
    factor: number,
    isTrafficLight: boolean,
  ) {
    if (!bid) return null;
    return (bid.items ?? []).reduce((sum: number, item: any) => {
      const levels = itemLevels(item);
      return (
        sum +
        effectiveAmount(
          levels.green,
          levels.yellow,
          levels.red,
          position,
          applySurcharge,
          factor,
          isTrafficLight,
        ) *
          item.quantity
      );
    }, 0);
  }

  return (
    <>
      <Container fluid className="mt-4">
        <h1>{applyDisplayName("Beitragsrunde Auswertung", displayName)}</h1>
        {resultMessage && <p className="text-success">{resultMessage}</p>}
        {errorReport.length > 0 && (
          <Card className="mb-4 border-danger">
            <Card.Header className="bg-danger text-white">
              {"Fehler bei der Vertragserzeugung"}
            </Card.Header>
            <Card.Body>
              <Table size="sm" className="mb-0">
                <thead>
                  <tr>
                    <th>{"Mitglied"}</th>
                    <th>{"Produkt"}</th>
                    <th>{"Grund"}</th>
                  </tr>
                </thead>
                <tbody>
                  {errorReport.map((error, index) => (
                    <tr key={index}>
                      <td>{error.memberName ?? error.memberId}</td>
                      <td>{error.productName ?? "–"}</td>
                      <td>{error.error ?? "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        )}

        {dynamicProjection && (
          <Card className="mb-4">
            <Card.Body>
              <div className="d-flex flex-row justify-content-between align-items-center">
                <Card.Title className="mb-0">
                  {isTrafficLight
                    ? "Finanzierung & dynamisches Durchschnittsgebot"
                    : "Finanzierung & Durchschnittsgebot"}
                </Card.Title>
                <Form.Check
                  type="switch"
                  label={"Auto-Verlängerung berücksichtigen"}
                  checked={includeAutoRenewed}
                  onChange={(event) =>
                    setIncludeAutoRenewed(event.target.checked)
                  }
                />
              </div>
              {isTrafficLight ? (
                <>
                  <p className="text-muted mt-2 mb-1">
                    {"Der Regler ist das"}{" "}
                    <strong>{"gewählte Solidaritätsniveau"}</strong>
                    {": eine Skala von"} <em>{"Grün (0, Wunsch)"}</em> {"über"}{" "}
                    <em>{"Gelb (50, Zufrieden)"}</em> {"bis"}{" "}
                    <em>{"Rot (100, Schmerzgrenze)"}</em>
                    {". Zu jedem Gebot gehören drei Beträge —"}{" "}
                    <em>{"Wunsch (Grün)"}</em>, <em>{"Zufrieden (Gelb)"}</em>,{" "}
                    <em>{"Schmerzgrenze (Rot)"}</em>
                    {
                      ". Die Regler-Position legt fest, mit welchem dieser Beträge gerechnet wird (dazwischen stufenlos interpoliert)."
                    }
                  </p>
                  <p className="text-muted small mb-2">
                    <strong>{"Warum solidarisch?"}</strong>{" "}
                    {"Je weiter der Regler in Richtung"} <em>{"Rot"}</em>
                    {
                      ", desto mehr zahlen die Bietenden (bis zur Schmerzgrenze) und desto stärker tragen sie den Bedarf mit — dadurch"
                    }{" "}
                    <strong>{"sinkt"}</strong>{" "}
                    {
                      "das Durchschnittsgebot für alle, die nicht geboten haben. In Richtung"
                    }{" "}
                    <em>{"Grün"}</em>{" "}
                    {
                      "zahlen die Bietenden nur ihren Wunsch, dann übernehmen die übrigen mehr. In beiden Fällen bleibt das Ziel bei voller Auslastung gedeckt."
                    }
                  </p>
                </>
              ) : (
                <p className="text-muted mt-2 mb-2">
                  {bidLevels > 1 ? (
                    <>
                      {interpolate(
                        "Jedes Gebot hat mehrere Beträge (Gebot 1 bis Gebot {count}).",
                        { count: bidLevels },
                      )}{" "}
                      {
                        "Gebot 1 ist der Wunschbetrag; reicht er nicht, gilt automatisch die nächste Stufe. Die Bietenden zahlen den Betrag der gültigen Stufe; alle, die nicht geboten haben — Auto-Verlängerer und Mitglieder, die nach der"
                      }{" "}
                      {applyDisplayName("Beitragsrunde", displayName)}{" "}
                      {"— zahlen dasselbe"}{" "}
                      <strong>{"dynamische Durchschnittsgebot"}</strong>
                      {
                        ". Es ist so berechnet, dass bei voller Auslastung der Ziel-Deckungsbetrag gedeckt ist."
                      }
                    </>
                  ) : (
                    <>
                      {
                        "Jedes Gebot hat genau einen Betrag. Die Bietenden zahlen diesen Betrag; alle, die nicht geboten haben — Auto-Verlängerer und Mitglieder, die nach der"
                      }{" "}
                      {applyDisplayName("Beitragsrunde", displayName)}{" "}
                      {"— zahlen dasselbe"}{" "}
                      <strong>{"dynamische Durchschnittsgebot"}</strong>
                      {
                        ". Es ist so berechnet, dass bei voller Auslastung der Ziel-Deckungsbetrag gedeckt ist."
                      }
                    </>
                  )}
                </p>
              )}
              <div className="mt-1 mb-2">
                <Button
                  variant="link"
                  className="p-0 small"
                  onClick={() => setShowFormula(!showFormula)}
                >
                  {showFormula
                    ? "Wie wird gerechnet? ausblenden"
                    : "Wie wird gerechnet?"}
                </Button>
                <Collapse in={showFormula}>
                  <div className="text-muted small mt-1">
                    {isTrafficLight ? (
                      <p className="mb-1">
                        <strong>
                          {
                            "Der Regler interpoliert die drei Beträge deines Gebots."
                          }
                        </strong>{" "}
                        {
                          "Interpolieren heißt: Der Betrag wird gleichmäßig zwischen den beiden benachbarten Werten umgerechnet. Ganz links (Position 0) zählt nur der Wunsch (Grün), in der Mitte (50) der Zufrieden-Betrag (Gelb), ganz rechts (100) die Schmerzgrenze (Rot)."
                        }
                      </p>
                    ) : bidLevels > 1 ? (
                      <p className="mb-1">
                        <strong>{"Der Regler wählt die Gebotsstufe."}</strong>{" "}
                        {interpolate(
                          "Gebot 1 ist der Wunschbetrag; reicht er nicht, gilt automatisch die nächste Stufe (Gebot 1 bis Gebot {count}). Gerechnet wird mit dem Betrag der gewählten Stufe.",
                          { count: bidLevels },
                        )}
                      </p>
                    ) : (
                      <p className="mb-1">
                        <strong>
                          {"Alle Gebote haben genau einen Betrag."}
                        </strong>{" "}
                        {"Gerechnet wird mit diesem Betrag."}
                      </p>
                    )}
                    <p className="mb-1">
                      <strong>{"Bietende Ø"}</strong>{" "}
                      {
                        "= Summe aller Gebote der Saison ÷ gebotene Ernteanteile ÷ 12 (Monate). Das ist der durchschnittliche Beitrag pro Anteil und Monat."
                      }
                    </p>
                    <p className="mb-1">
                      <strong>{"Nicht-Bietende Ø"}</strong>{" "}
                      {
                        "= (Ziel − Gebote der Bietenden − Mitgliedsbeiträge − Lieferzuschlag) ÷ (Auto-Verlängerer-Anteile + offene Anteile) ÷ 12. Er ist so gewählt, dass das Ziel bei voller Auslastung gedeckt ist."
                      }
                      {nonBiddersMinAverage && (
                        <>
                          {" "}
                          {
                            "Nicht-Bietende zahlen dabei mindestens das Ø-Gebot der Bietenden."
                          }
                        </>
                      )}
                      {membershipIncludedInProductType && (
                        <>
                          {" "}
                          {
                            "Mitgliedsbeiträge: an den Ernteanteil angerechnet, daher nicht separat gerechnet."
                          }
                        </>
                      )}
                      {!membershipIncludedInProductType &&
                        membershipFeesApply && (
                          <>
                            {" "}
                            {
                              "Mitgliedsbeiträge: werden als eigener fester Beitrag gerechnet."
                            }
                          </>
                        )}
                    </p>
                    <p className="mb-1">
                      <strong>{"Summe bei voller Auslastung"}</strong>{" "}
                      {
                        "= Gebote der Bietenden + Mitgliedsbeiträge + Lieferzuschlag + Nicht-Bietende Ø × (Auto-Verlängerer-Anteile + offene Anteile) × 12. Bei voller Auslastung deckt diese Summe das Ziel."
                      }
                    </p>
                    <p className="mt-1 mb-0">
                      {
                        "Ein optionaler Aufschlag erhöht die Gebote und/oder den Ø; beim Ampel nie über die Schmerzgrenze (Rot) hinaus."
                      }
                    </p>
                  </div>
                </Collapse>
              </div>
              <ul className="text-muted small mb-3">
                <li>
                  <strong>{"Bietende Mitglieder"}</strong>{" "}
                  {"zahlen ihr abgegebenes Gebot"}
                  {isTrafficLight
                    ? " — auf dem gewählten Niveau"
                    : bidLevels > 1
                      ? " — auf der gewählten Stufe"
                      : ""}{" "}
                  {"im Ø"}{" "}
                  <strong>
                    {formatEuro(dynamicProjection.bidderAveragePerMonth)}
                  </strong>{" "}
                  {"/ Anteil / Monat."}
                </li>
                <li>
                  <strong>{"Alle, die nicht geboten haben"}</strong>{" "}
                  {"— Auto-Verlängerer und Mitglieder, die nach der"}{" "}
                  {applyDisplayName("Beitragsrunde", displayName)}{" "}
                  {"— zahlen dasselbe"}{" "}
                  <strong>{"dynamische Durchschnittsgebot"}</strong>{" "}
                  <strong>
                    {formatEuro(dynamicProjection.averagePerSharePerMonth)}
                  </strong>{" "}
                  {interpolate(
                    "/ Anteil / Monat. Es ist so berechnet, dass bei voller Auslastung ({capacity} Anteile) der Ziel-Deckungsbetrag ({target}) gedeckt ist.",
                    {
                      capacity: formatNumber(
                        financingProjection.capacityShares,
                      ),
                      target: formatEuro(dynamicProjection.target),
                    },
                  )}
                </li>
                {isTrafficLight && (
                  <li>
                    {"Regler nach"} <em>{"Grün"}</em>{" "}
                    {"→ Bietende zahlen weniger ⇒ das Durchschnittsgebot"}{" "}
                    <strong>{"steigt"}</strong>
                    {"; Regler nach"} <em>{"Rot"}</em>{" "}
                    {"→ Bietende zahlen mehr ⇒ das Durchschnittsgebot"}{" "}
                    <strong>{"sinkt"}</strong>.
                  </li>
                )}
              </ul>

              {isTrafficLight && (
                <>
                  <div className="position-relative">
                    <div
                      style={{
                        height: "0.5rem",
                        borderRadius: "0.25rem",
                        background:
                          "linear-gradient(90deg, #198754 0%, #ffc107 50%, #dc3545 100%)",
                        opacity: 0.5,
                      }}
                    />
                    <Form.Range
                      min={0}
                      max={100}
                      step={1}
                      value={trafficLightPosition}
                      onChange={(event) =>
                        setTrafficLightPosition(Number(event.target.value))
                      }
                      disabled={averageBidLocked}
                      className="w-100"
                      style={{ marginTop: "-0.95rem" }}
                      aria-label={"Solidaritätsniveau"}
                    />
                  </div>
                  <div className="d-flex justify-content-between small text-muted">
                    <span>{"Grün (Wunsch)"}</span>
                    <span>{"Gelb (Zufrieden)"}</span>
                    <span>{"Rot (Schmerzgrenze)"}</span>
                  </div>
                </>
              )}

              {!isTrafficLight && bidLevels > 1 && (
                <>
                  <p className="text-muted small mb-1">
                    {"Empfohlene Stufe:"}{" "}
                    <strong>
                      {interpolate("Gebot {level}", {
                        level: recommendedLevel,
                      })}
                    </strong>{" "}
                    {"(erste Stufe mit mindestens 90 % Deckung)."}
                  </p>
                  <Form.Range
                    min={1}
                    max={bidLevels}
                    step={1}
                    value={levelFromPosition(trafficLightPosition, bidLevels)}
                    onChange={(event) =>
                      setTrafficLightPosition(
                        (Number(event.target.value) - 1) * 50,
                      )
                    }
                    disabled={averageBidLocked}
                    className="w-100"
                    aria-label={"Gebotsstufe"}
                  />
                  <div className="d-flex justify-content-between small text-muted">
                    {Array.from({ length: bidLevels }, (_, i) => i + 1).map(
                      (level) => (
                        <span key={level}>
                          {interpolate("Gebot {level}", { level })}
                          {level === recommendedLevel ? " (empfohlen)" : ""}
                        </span>
                      ),
                    )}
                  </div>
                </>
              )}

              <div className="row mt-3 align-items-center">
                <div className="col-md-6">
                  <div className="display-6">
                    {formatEuro(dynamicProjection.bidderAveragePerMonth)}
                  </div>
                  <div>
                    <span className="text-muted small">
                      {"/ Anteil / Monat für"}{" "}
                    </span>
                    <span className="fw-bold fs-5">{"Bietende Ø"}</span>
                  </div>
                  <div className="text-muted small mb-2">
                    = {formatEuro(dynamicProjection.bidderAveragePerMonth * 12)}{" "}
                    {"/ Anteil / Jahr Ø"}
                  </div>
                  <div className="display-6">
                    {formatEuro(dynamicProjection.averagePerSharePerMonth)}
                  </div>
                  <div>
                    <span className="text-muted small">
                      {"/ Anteil / Monat für"}{" "}
                    </span>
                    <span className="fw-bold fs-5">{"Nicht-Bietende"}</span>
                  </div>
                  <div className="text-muted small">
                    ={" "}
                    {formatEuro(dynamicProjection.averagePerSharePerMonth * 12)}{" "}
                    {"/ Anteil / Jahr"}
                  </div>
                </div>
                <div className="col-md-6">
                  <DeckungAuslastungBars
                    utilization={dynamicProjection.utilization}
                    currentShares={dynamicProjection.currentShares}
                    capacityShares={dynamicProjection.capacityShares}
                    currentCoverage={dynamicProjection.currentCoverage}
                    currentTotal={dynamicProjection.currentTotal}
                    target={dynamicProjection.target}
                  />
                </div>
              </div>

              <div className="mt-3">
                <Button
                  variant="link"
                  className="p-0"
                  onClick={() => setShowSurcharge(!showSurcharge)}
                >
                  {showSurcharge
                    ? "Aufschlag ausblenden"
                    : "Aufschlag anzeigen"}
                </Button>
                <Collapse in={showSurcharge}>
                  <div className="mt-2 p-3 bg-light rounded">
                    <h6 className="mb-1">
                      {"Aufschlag (Ausgleich offener Anteile)"}
                    </h6>
                    <p className="text-muted small mb-2">
                      {
                        "Hebe die Beiträge an, damit das Ziel auch ohne die offenen Anteile gedeckt ist."
                      }
                      {isTrafficLight ? (
                        <>
                          {" "}
                          {"Der Aufschlag geht"}{" "}
                          <strong>{"nie über die Schmerzgrenze (Rot)"}</strong>.
                        </>
                      ) : null}
                    </p>
                    <Form.Group className="mb-2">
                      <Form.Label className="small mb-0">
                        {"Aufschlag:"} <strong>{surchargePercent} %</strong>
                      </Form.Label>
                      <Form.Range
                        min={0}
                        max={100}
                        step={1}
                        value={surchargePercent}
                        onChange={(event) =>
                          setSurchargePercent(Number(event.target.value))
                        }
                        disabled={averageBidLocked}
                        aria-label={"Aufschlag"}
                      />
                    </Form.Group>
                    <div className="d-flex gap-3 flex-wrap">
                      <Form.Check
                        type="switch"
                        label={"Auf Gebote"}
                        checked={surchargeOnBids}
                        onChange={(event) =>
                          setSurchargeOnBids(event.target.checked)
                        }
                        disabled={averageBidLocked}
                      />
                      <Form.Check
                        type="switch"
                        label={"Auf Durchschnittsgebot"}
                        checked={surchargeOnAverage}
                        onChange={(event) =>
                          setSurchargeOnAverage(event.target.checked)
                        }
                        disabled={averageBidLocked}
                      />
                    </div>
                    <div className="d-flex justify-content-between align-items-center mt-2">
                      <span>
                        {"Deckung durch aktuelle Mitglieder (ohne Nachzügler)"}
                      </span>
                      <Badge
                        bg={coverageVariant(dynamicProjection.currentCoverage)}
                      >
                        {formatPercent(dynamicProjection.currentCoverage)}
                      </Badge>
                    </div>
                    <ProgressBar
                      className="mt-1"
                      variant={coverageVariant(
                        dynamicProjection.currentCoverage,
                      )}
                      now={Math.min(dynamicProjection.currentCoverage, 100)}
                      label={formatPercent(dynamicProjection.currentCoverage)}
                    />
                  </div>
                </Collapse>
              </div>

              <div className="mt-3 d-flex align-items-center gap-2 flex-wrap">
                <Button
                  variant="primary"
                  onClick={lockAverageBid}
                  disabled={averageBidLocked}
                >
                  {"Durchschnittsgebot festlegen"}
                </Button>
                <Button
                  variant="outline-secondary"
                  onClick={unlockAverageBid}
                  disabled={!averageBidLocked || contractsCreatedAt != null}
                >
                  {"Sperre aufheben"}
                </Button>
                {averageBidLocked && (
                  <div className="p-2 bg-light rounded small">
                    <strong>{"Gesperrtes Durchschnittsgebot"}</strong>
                    {": "}
                    {interpolate("Bietende {amount} / Anteil / Monat", {
                      amount: formatEuro(
                        Number(data?.lockedBidderAveragePerSharePerMonth ?? 0),
                      ),
                    })}
                    {" · "}
                    {interpolate("Nicht-Bietende {amount} / Anteil / Monat", {
                      amount: formatEuro(
                        Number(data?.lockedAverageBidPerSharePerMonth ?? 0),
                      ),
                    })}
                    {" · "}
                    {interpolate("Aufschlag {percent} %", {
                      percent: Number(data?.lockedSurchargePercent ?? 0),
                    })}
                    {" ("}
                    {data?.lockedSurchargeOnBids &&
                    data?.lockedSurchargeOnAverage
                      ? "auf Gebote und Durchschnittsgebot"
                      : data?.lockedSurchargeOnBids
                        ? "auf Gebote"
                        : data?.lockedSurchargeOnAverage
                          ? "auf Durchschnittsgebot"
                          : "inaktiv"}
                    {")"}
                  </div>
                )}
                {contractsCreatedAt != null && (
                  <Badge bg="warning" text="dark">
                    {"Verträge erzeugt"}
                  </Badge>
                )}
              </div>

              <Table size="sm" className="mt-3 mb-0">
                <tbody>
                  <tr>
                    <td>
                      {isTrafficLight
                        ? interpolate("Bietende (Niveau {position})", {
                            position: trafficLightPosition,
                          })
                        : bidLevels > 1
                          ? interpolate("Bietende (Gebot {level})", {
                              level: levelFromPosition(
                                trafficLightPosition,
                                bidLevels,
                              ),
                            })
                          : "Bietende (Gebotsbetrag)"}
                    </td>
                    <td className="text-end">
                      {formatEuro(dynamicProjection.baseBidReached)}
                    </td>
                  </tr>
                  {includeAutoRenewed && (
                    <tr>
                      <td>
                        {interpolate("Auto-Verlängerer ({count} Anteile × Ø)", {
                          count: formatNumber(financingProjection.autoShares),
                        })}
                      </td>
                      <td className="text-end">
                        {formatEuro(dynamicProjection.baseAutoTotal)}
                      </td>
                    </tr>
                  )}
                  {Number(financingProjection.deliveryChargePerYear ?? 0) >
                    0 && (
                    <tr>
                      <td>{"Lieferzuschlag"}</td>
                      <td className="text-end">
                        {formatEuro(
                          Number(financingProjection.deliveryChargePerYear),
                        )}
                      </td>
                    </tr>
                  )}
                  {Number(financingProjection.membershipPerYear ?? 0) > 0 && (
                    <tr>
                      <td>{"Mitgliedschaft"}</td>
                      <td className="text-end">
                        {formatEuro(
                          Number(financingProjection.membershipPerYear),
                        )}
                      </td>
                    </tr>
                  )}
                  {surchargePercent > 0 && (
                    <tr>
                      <td>
                        {interpolate("Aufschlag (+{percent} %)", {
                          percent: surchargePercent,
                        })}
                        {surchargeOnBids && surchargeOnAverage
                          ? " auf Gebote und Durchschnittsgebot"
                          : surchargeOnBids
                            ? " auf Gebote"
                            : surchargeOnAverage
                              ? " auf Durchschnittsgebot"
                              : " (inaktiv)"}
                      </td>
                      <td className="text-end">
                        +{formatEuro(dynamicProjection.surchargeTotal)}
                      </td>
                    </tr>
                  )}
                  <tr className="fw-bold table-light">
                    <td>{"Aktuelle Deckung"}</td>
                    <td className="text-end">
                      {formatEuro(dynamicProjection.currentTotal)}
                    </td>
                  </tr>
                  <tr>
                    <td className="text-muted">{"Differenz zum Ziel"}</td>
                    <td className="text-end text-muted">
                      {formatEuro(
                        dynamicProjection.target -
                          dynamicProjection.currentTotal,
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      {interpolate("Nachzügler ({count} Anteile × Ø)", {
                        count: formatNumber(
                          financingProjection.remainingShares,
                        ),
                      })}
                    </td>
                    <td className="text-end">
                      {formatEuro(dynamicProjection.baseLatecomerTotal)}
                    </td>
                  </tr>
                  <tr className="fw-bold">
                    <td>{"Summe bei voller Auslastung"}</td>
                    <td className="text-end">
                      {formatEuro(dynamicProjection.total)}
                    </td>
                  </tr>
                  <tr>
                    <td>{"Ziel-Deckungsbetrag"}</td>
                    <td className="text-end">
                      {formatEuro(dynamicProjection.target)}
                    </td>
                  </tr>
                  <tr>
                    <td>{"Anteile geboten / Ziel"}</td>
                    <td className="text-end">
                      {formatNumber(
                        Number(financingProjection.bidShares) +
                          (includeAutoRenewed
                            ? Number(financingProjection.autoShares)
                            : 0),
                      )}{" "}
                      / {formatNumber(financingProjection.capacityShares)}
                    </td>
                  </tr>
                </tbody>
              </Table>

              {isTrafficLight && (
                <div className="mt-3">
                  <Button
                    variant="link"
                    className="p-0"
                    onClick={() => setShowExample(!showExample)}
                  >
                    {showExample ? "Beispiel ausblenden" : "Beispiel anzeigen"}
                  </Button>
                  <Collapse in={showExample}>
                    <div>
                      <p className="text-muted small mt-2 mb-1">
                        {interpolate(
                          "Beispielgebote und ihr effektiver Betrag bei der aktuellen Regler-Position ({position}):",
                          { position: trafficLightPosition },
                        )}
                      </p>
                      <Table size="sm" className="mb-0">
                        <thead>
                          <tr>
                            <th>{"Gebot"}</th>
                            <th className="text-end">{"Grün (Wunsch)"}</th>
                            <th className="text-end">{"Gelb (Zufrieden)"}</th>
                            <th className="text-end">
                              {"Rot (Schmerzgrenze)"}
                            </th>
                            <th className="text-end">
                              {interpolate("Effektiv (Position {position})", {
                                position: trafficLightPosition,
                              })}
                              {surchargeOnBids && surchargePercent > 0
                                ? interpolate(
                                    ", inkl. Aufschlag +{percent} %",
                                    { percent: surchargePercent },
                                  )
                                : ""}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {EXAMPLE_BIDS.map((bid) => (
                            <tr key={bid.label}>
                              <td>{bid.label}</td>
                              <td className="text-end">
                                {formatEuro(bid.green)}
                              </td>
                              <td className="text-end">
                                {formatEuro(bid.yellow)}
                              </td>
                              <td className="text-end">
                                {formatEuro(bid.red)}
                              </td>
                              <td className="text-end fw-bold">
                                {formatEuro(
                                  effectiveAmount(
                                    bid.green,
                                    bid.yellow,
                                    bid.red,
                                    trafficLightPosition,
                                    surchargeOnBids,
                                    surchargeFactor,
                                    isTrafficLight,
                                  ),
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  </Collapse>
                </div>
              )}

              <div className="mt-3">
                <Button
                  variant="link"
                  className="p-0"
                  onClick={() => setShowProjection(!showProjection)}
                >
                  {showProjection
                    ? "12-Monats-Prognose ausblenden"
                    : "12-Monats-Prognose anzeigen"}
                </Button>
                <Collapse in={showProjection}>
                  <div className="mt-2 p-3 bg-light rounded">
                    <h6 className="mb-1">{"12-Monats-Prognose"}</h6>
                    <p className="text-muted small mb-2">
                      {
                        "Geschätzte Anzahl neuer Mitglieder (je 1 Anteil) pro Monat. Der Graph zeigt den kumulierten Saldo (Beiträge − anteilige Kosten) über 12 Monate: unter der 0-Linie = Verlust, Erreichen der 0-Linie = Break-even."
                      }
                    </p>
                    <Form.Group className="mb-2">
                      <Form.Label className="small mb-0">
                        {"Neue Mitglieder je Monat:"}{" "}
                        <strong>{newMembersPerMonth}</strong>
                      </Form.Label>
                      <Form.Range
                        min={1}
                        max={Math.max(
                          1,
                          Math.ceil(twelveMonthProjection?.openShares ?? 1),
                        )}
                        step={1}
                        value={newMembersPerMonth}
                        onChange={(event) =>
                          setNewMembersPerMonth(Number(event.target.value))
                        }
                        aria-label={"Neue Mitglieder je Monat"}
                      />
                    </Form.Group>
                    <div className="mb-2">
                      {twelveMonthProjection?.breakEvenMonth != null ? (
                        <Badge bg="success">
                          {interpolate(
                            "Break-even ab Monat {month} — positiver Saldo nach 12 Monaten: +{amount}",
                            {
                              month: twelveMonthProjection.breakEvenMonth,
                              amount: formatEuro(
                                twelveMonthProjection.saldoAfterTwelveMonths,
                              ),
                            },
                          )}
                        </Badge>
                      ) : (
                        <Badge bg="danger">
                          {interpolate(
                            "Kein Break-even in 12 Monaten — Saldo: {amount}",
                            {
                              amount: formatEuro(
                                twelveMonthProjection?.saldoAfterTwelveMonths ??
                                  0,
                              ),
                            },
                          )}
                        </Badge>
                      )}
                    </div>
                    <Bar
                      data={
                        twelveMonthProjection?.chartData ?? {
                          labels: [],
                          datasets: [],
                        }
                      }
                      options={{
                        responsive: true,
                        scales: {
                          members: {
                            position: "left",
                            suggestedMin: 0,
                            title: {
                              display: true,
                              text: "Neue Mitglieder (kumuliert)",
                            },
                          },
                          saldo: {
                            position: "right",
                            grid: { drawOnChartArea: false },
                            title: {
                              display: true,
                              text: "Saldo (€)",
                            },
                          },
                        },
                      }}
                    />
                  </div>
                </Collapse>
              </div>
            </Card.Body>
          </Card>
        )}

        {pickupLocationsEnabled && (
          <Card className="mb-4">
            <Card.Body>
              <Card.Title>{"Abholort-Füllstand"}</Card.Title>
              <div className="row">
                <div className="col-md-6">
                  <Bar
                    data={pickupChartData}
                    options={{
                      responsive: true,
                      scales: { y: { suggestedMin: 0 } },
                    }}
                  />
                </div>
                <div className="col-md-6">
                  <Table striped hover size="sm" responsive>
                    <thead>
                      <tr>
                        <th>{"Verteilstation"}</th>
                        <th>{"Kapazität"}</th>
                        <th>{"Nachfrage"}</th>
                        <th>{"Füllstand"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pickupFill.map((entry: any) => (
                        <tr key={entry.pickupLocationId}>
                          <td>{entry.pickupLocationName}</td>
                          <td>{formatNumber(entry.capacity)}</td>
                          <td>{formatNumber(entry.demand)}</td>
                          <td style={{ minWidth: "140px" }}>
                            <ProgressBar
                              now={Math.min(entry.fillPercent ?? 0, 100)}
                              label={formatPercent(entry.fillPercent)}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              </div>
            </Card.Body>
          </Card>
        )}

        <Card className="mb-4">
          <Card.Body>
            <div className="d-flex flex-row justify-content-between align-items-center">
              <Card.Title className="mb-0">{"Gebote"}</Card.Title>
              <div className="d-flex gap-2">
                <Form.Select
                  size="sm"
                  value={filter}
                  onChange={(event) => setFilter(event.target.value)}
                >
                  <option value="active_in_contract_period">
                    {"Aktive Mitglieder (Vertragsperiode)"}
                  </option>
                  <option value="all">{"Alle Mitglieder"}</option>
                  <option value="has_bid">{"Hat geboten"}</option>
                  <option value="no_bid">{"Hat nicht geboten"}</option>
                  {data?.autoRenewedEnabled && (
                    <option value="auto_renewed">{"Auto-verlängert"}</option>
                  )}
                </Form.Select>
                <Form.Select
                  size="sm"
                  value={sort}
                  onChange={(event) => setSort(event.target.value)}
                >
                  <option value="name">{"Sortierung: Name"}</option>
                  <option value="date">{"Sortierung: Datum"}</option>
                </Form.Select>
                <Form.Check
                  type="switch"
                  id="bidding-round-toggle-emails"
                  className="text-nowrap small"
                  label={"E-Mail"}
                  checked={showEmails}
                  onChange={(event) => setShowEmails(event.target.checked)}
                />
                <Button
                  variant="outline-success"
                  size="sm"
                  onClick={openCreateBidModal}
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
                        onChange={toggleAllBids}
                      />
                    </th>
                    <th>{"Mitglied"}</th>
                    {showEmails && <th>{"E-Mail"}</th>}
                    <th>{"Gebot"}</th>
                    <th>{"Positionen"}</th>
                    {isTrafficLight ? (
                      <th className="text-nowrap">
                        {"Grün/Gelb/Rot (€/Monat)"}
                      </th>
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
                        ? isTrafficLight
                          ? interpolate(
                              "Effektiv (Pos. {position}, +{percent} %)",
                              {
                                position: trafficLightPosition,
                                percent: surchargePercent,
                              },
                            )
                          : interpolate(
                              "Effektiv (Stufe {level}, +{percent} %)",
                              {
                                level: levelFromPosition(
                                  trafficLightPosition,
                                  bidLevels,
                                ),
                                percent: surchargePercent,
                              },
                            )
                        : isTrafficLight
                          ? interpolate("Effektiv (Pos. {position})", {
                              position: trafficLightPosition,
                            })
                          : interpolate("Effektiv (Stufe {level})", {
                              level: levelFromPosition(
                                trafficLightPosition,
                                bidLevels,
                              ),
                            })}
                    </th>
                    <th className="text-nowrap">{"Abholort 1./2."}</th>
                    <th>{"Aktualisiert"}</th>
                    <th>{"Status"}</th>
                    <th>{"Aktionen"}</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((entry: any) => (
                    <tr key={entry.memberId}>
                      <td>
                        {entry.bid && (
                          <Form.Check
                            checked={selectedBidIds.includes(entry.bid.id)}
                            onChange={() => toggleBid(entry.bid.id)}
                          />
                        )}
                        {!entry.hasBid && entry.isAutoRenewed && (
                          <Form.Check
                            checked={selectedAutoRenewedMemberIds.includes(
                              entry.memberId,
                            )}
                            onChange={() =>
                              toggleAutoRenewedMember(entry.memberId)
                            }
                          />
                        )}
                      </td>
                      <td>
                        <a href={`/tapir/members/${entry.memberId}`}>
                          {entry.memberName}
                        </a>
                      </td>
                      {showEmails && <td>{entry.memberEmail}</td>}
                      <td>
                        {entry.hasBid ? (
                          <span className="badge bg-success">{"Gebot"}</span>
                        ) : entry.isAutoRenewed ? (
                          <span className="badge bg-info text-dark">
                            {"Auto-verlängert"}
                          </span>
                        ) : (
                          <span className="badge bg-secondary">
                            {"Kein Gebot"}
                          </span>
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
                          ? (isTrafficLight
                              ? ([1, 2, 3] as const)
                              : Array.from(
                                  { length: bidLevels },
                                  (_, i) => (i + 1) as 1 | 2 | 3,
                                )
                            )
                              .map((level) =>
                                formatEuro(bidAmountForLevel(entry.bid, level)),
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
                                  trafficLightPosition,
                                  surchargeOnBids,
                                  surchargeFactor,
                                  isTrafficLight,
                                ),
                              )}{" "}
                              {"/ Monat"}
                            </div>
                            <div>
                              {formatEuro(
                                (bidAmountAtPosition(
                                  entry.bid,
                                  trafficLightPosition,
                                  surchargeOnBids,
                                  surchargeFactor,
                                  isTrafficLight,
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
                              {formatEuro(entry.autoRenewedAmountPerYear)}{" "}
                              {"/ Jahr"}
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
                          ? new Date(entry.bid.updatedAt).toLocaleDateString(
                              "de-DE",
                            )
                          : "–"}
                      </td>
                      <td>
                        {entry.bid?.enteredByAdmin && (
                          <span className="badge bg-secondary me-1">
                            {"von Admin erfasst"}
                          </span>
                        )}
                        {entry.bid?.adminConfirmed ? (
                          <span className="badge bg-success">
                            {"bestätigt"}
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
                              onClick={() => openEditBidModal(entry)}
                            >
                              {"Bearbeiten"}
                            </Button>
                            <Button
                              variant="outline-danger"
                              size="sm"
                              onClick={() => deleteBid(entry)}
                            >
                              {"Löschen"}
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="outline-success"
                            size="sm"
                            onClick={() => {
                              setCreateMemberId(entry.memberId);
                              setBidModalMemberName(entry.memberName);
                              setEditingBid(null);
                              setBidAdminConfirmed(false);
                              setBidEnteredByAdmin(true);
                              setBidPickupLocationId("");
                              setBidItems(emptyBidItems());
                              setShowBidModal(true);
                            }}
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
              onClick={confirmBids}
              disabled={selectedBidIds.length === 0}
            >
              {"Ausgewählte bestätigen"}
            </Button>{" "}
            <Button
              variant="primary"
              onClick={openContractsModal}
              disabled={!canCreateContracts}
              title={
                !averageBidLocked
                  ? "Sperren Sie das Durchschnittsgebot, bevor Sie Verträge erzeugen."
                  : !hasContractSelection
                    ? "Wählen Sie zuerst mindestens ein Gebot oder einen Auto-Verlängerer aus."
                    : !selectedBidsConfirmed
                      ? "Alle ausgewählten Gebote müssen bestätigt sein, bevor Verträge erzeugt werden."
                      : undefined
              }
            >
              {"Verträge erzeugen"}
            </Button>{" "}
            {!canCreateContracts &&
              (!averageBidLocked ? (
                <Button
                  variant="link"
                  className="p-0 align-baseline"
                  onClick={lockAverageBid}
                >
                  {
                    "Sperren Sie das Durchschnittsgebot, bevor Sie Verträge erzeugen."
                  }
                </Button>
              ) : (
                <span className="text-danger small">
                  {!hasContractSelection
                    ? "Wählen Sie zuerst mindestens ein Gebot oder einen Auto-Verlängerer aus."
                    : "Alle ausgewählten Gebote müssen bestätigt sein, bevor Verträge erzeugt werden."}
                </span>
              ))}
            <a
              className="btn btn-outline-secondary"
              href={`/bidding_rounds/api/${roundId}/export.csv`}
            >
              {"CSV-Export"}
            </a>
            {contractsCreatedAt != null && (
              <>
                {" "}
                <Button variant="outline-danger" onClick={deleteContracts}>
                  {"Verträge löschen"}
                </Button>
              </>
            )}
          </Card.Body>
        </Card>

        {contracts.length > 0 && (
          <Card className="mb-4">
            <Card.Body>
              <Card.Title>{"Erzeugte Verträge"}</Card.Title>
              <Table size="sm" responsive>
                <thead>
                  <tr>
                    <th>{"Mitglied"}</th>
                    <th>{"Status"}</th>
                    <th>{"Positionen"}</th>
                    {isSolidarityRound && (
                      <th className="text-end">{"Standard / Monat"}</th>
                    )}
                    {isSolidarityRound && (
                      <th className="text-end">
                        {"Solidaritätsbeitrag / Monat"}
                      </th>
                    )}
                    <th className="text-end">{"Gesamt / Monat"}</th>
                    <th className="text-end">{"Gesamt / Jahr"}</th>
                    <th>{"Verteilstation"}</th>
                    <th>{"Vertrag"}</th>
                  </tr>
                </thead>
                <tbody>
                  {contracts.map((contract: any) => (
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
                          <span className="badge bg-info text-dark">
                            {"Auto-verlängert"}
                          </span>
                        ) : (
                          <span className="badge bg-success">{"Gebot"}</span>
                        )}
                      </td>
                      <td>{renderContractItems(contract.items)}</td>
                      {isSolidarityRound && (
                        <td className="text-end">
                          {formatEuro(Number(contract.standardAmountPerMonth))}
                        </td>
                      )}
                      {isSolidarityRound && (
                        <td className="text-end">
                          {formatEuro(
                            Number(contract.contributionAmountPerMonth),
                          )}
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
                          href={`/tapir/contracts?period=${data?.growingPeriodId}&member=${contract.memberId}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {"Vertrag"}
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        )}
      </Container>

      <Modal
        show={showContractsModal}
        onHide={() => setShowContractsModal(false)}
        centered={true}
        size="lg"
      >
        <Modal.Header closeButton>
          <h5 className="mb-0">{"Verträge erzeugen"}</h5>
        </Modal.Header>
        <Modal.Body>
          {checkLoading ? (
            <div className="d-flex align-items-center gap-2">
              <Spinner animation="border" size="sm" />
              <span>{"Verträge werden geprüft…"}</span>
            </div>
          ) : (
            <>
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
                    {checkErrors.map((error: any, index: number) => (
                      <tr key={index}>
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
                onChange={(event) => setCreateAutoRenewed(event.target.checked)}
              />
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="outline-primary"
            onClick={runCheckContracts}
            disabled={checkLoading || createLoading}
          >
            {"Verträge prüfen"}
          </Button>
          <Button
            variant="primary"
            onClick={createContracts}
            disabled={checkLoading || createLoading}
          >
            {createLoading ? (
              <Spinner animation="border" size="sm" />
            ) : (
              "Verträge erzeugen"
            )}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowContractsModal(false)}
            disabled={createLoading}
          >
            {"Abbrechen"}
          </Button>
        </Modal.Footer>
      </Modal>

      <Modal
        show={showBidModal}
        onHide={() => setShowBidModal(false)}
        centered={true}
        size="lg"
      >
        <Modal.Header closeButton>
          <h5 className="mb-0">
            {editingBid ? "Gebot bearbeiten" : "Gebot erfassen"}
            {bidModalMemberName ? ` – ${bidModalMemberName}` : ""}
          </h5>
        </Modal.Header>
        <Modal.Body>
          <Form>
            {!editingBid && (
              <Form.Group className="mb-2">
                <Form.Label>{"Mitglied"}</Form.Label>
                <Form.Select
                  value={createMemberId}
                  onChange={(e) => {
                    setCreateMemberId(e.target.value);
                    const entry = members.find(
                      (m: any) => m.memberId === e.target.value,
                    );
                    setBidModalMemberName(entry?.memberName ?? "");
                  }}
                  required
                >
                  <option value={""}>–</option>
                  {members
                    .filter((entry: any) => !entry.hasBid)
                    .map((entry: any) => (
                      <option key={entry.memberId} value={entry.memberId}>
                        {entry.memberName}
                      </option>
                    ))}
                </Form.Select>
              </Form.Group>
            )}
            {bidItems.length === 0 ? (
              <p className="text-muted">
                {"Keine bietbaren Produkte für diese Runde."}
              </p>
            ) : (
              bidItems.map((item, index) => {
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
                          {(biddableProduct?.products ?? []).map(
                            (product: any) => (
                              <option key={product.id} value={product.id}>
                                {product.name}
                              </option>
                            ),
                          )}
                        </Form.Select>
                      </Form.Group>
                      {bidOptions.quantityEnabled && (
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
                      {isTrafficLight
                        ? TRAFFIC_LIGHT_LEVELS.map((level) => (
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
                                {getTrafficLightDefaultLabel(level)}
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
                              | "amount1"
                              | "amount2"
                              | "amount3";
                            return (
                              <Form.Group
                                className={"col-md-3 mb-2"}
                                key={level}
                              >
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
                    {bidItems.length > 1 && (
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
            {pickupLocationsEnabled && (
              <>
                <Form.Group className={"mt-3"}>
                  <Form.Label>{"Abholort (1. Wahl)"}</Form.Label>
                  <Form.Select
                    value={bidPickupLocationId}
                    onChange={(event) =>
                      setBidPickupLocationId(event.target.value)
                    }
                  >
                    <option value={""}>–</option>
                    {pickupLocations.map((location: any) => (
                      <option key={location.id} value={location.id}>
                        {location.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              </>
            )}
            <Form.Group className={"mt-3"}>
              <Form.Check
                type="switch"
                label={"von Admin erfasst"}
                checked={bidEnteredByAdmin}
                onChange={(event) => setBidEnteredByAdmin(event.target.checked)}
              />
            </Form.Group>
            <Form.Group className={"mt-2"}>
              <Form.Check
                type="switch"
                label={"Admin-Bestätigung"}
                checked={bidAdminConfirmed}
                onChange={(event) => setBidAdminConfirmed(event.target.checked)}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="primary" onClick={saveBid} disabled={savingBid}>
            {savingBid ? "Speichert…" : "Speichern"}
          </Button>
        </Modal.Footer>
      </Modal>

      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default BiddingRoundResults;
