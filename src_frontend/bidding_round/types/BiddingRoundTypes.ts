import { PublicPickupLocation } from "../../api-client";

export type BiddingRoundStep =
  | "loading"
  | "bidding_round_intro"
  | "bidding_round_pickup_location"
  | "bidding_round_summary"
  | "bidding_round_confirmation"
  | string;

export type BiddingRoundBidItem = {
  roundProductId: string;
  productId: string;
  quantity: number;
  amount1?: string | null;
  amount2?: string | null;
  amount3?: string | null;
};

export type BiddingRoundBid = {
  id: string;
  memberId: string;
  pickupLocationId: string | null;
  enteredByAdmin: boolean;
  adminConfirmed: Date | null;
  items: BiddingRoundBidItem[];
};

export type BiddingRoundRound = {
  id: string;
  name: string;
  status: string;
  biddingProcedure: "simple" | "traffic_light" | string;
  bidLevels: number;
  startAt: Date | null;
  endAt: Date;
  growingPeriodId: string | null;
};

export type BiddingRoundProduct = {
  id: string;
  name: string;
  referenceValue: string | null;
  minAmount: string | null;
};

export type BiddingRoundProductType = {
  id: string;
  productTypeId: string;
  productTypeName: string;
  products: BiddingRoundProduct[];
};

export type BiddingRoundPickupLocationUtilization = {
  capacity: string;
  demand: string;
  fillPercent: number | null;
  isFull: boolean;
};

export type BiddingRoundPickupLocation = PublicPickupLocation & {
  yearlyDeliveryCharge?: string | number | null;
  utilization?: BiddingRoundPickupLocationUtilization | null;
};

export type BiddingRoundPublicEvaluationLevel = {
  reachedPerYear: number | string;
  currentTotalPerYear: number | string;
  currentCoveragePercent: number;
  bidderAveragePerMonth: number | string;
};

export type BiddingRoundPublicEvaluation = {
  biddingProcedure: "simple" | "traffic_light" | string;
  bidLevels: number;
  recommendedLevel: number;
  trafficLightPosition: number;
  targetPerYear: number | string;
  capacityShares: number | string;
  currentShares: number | string;
  utilizationPercent: number;
  levels: {
    green: BiddingRoundPublicEvaluationLevel;
    yellow: BiddingRoundPublicEvaluationLevel;
    red: BiddingRoundPublicEvaluationLevel;
  };
};

export type BiddingRoundBidTexts = {
  productLabel: string;
  variantLabel: string;
  quantityLabel: string;
  amountLabel: string;
  referenceValueHint: string;
  simpleExplanation: string;
  trafficLightExplanation: string;
  simpleLevelsExplanation: string;
  level1Label: string;
  level2Label: string;
  level3Label: string;
  greenLabel: string;
  yellowLabel: string;
  redLabel: string;
  pickupLocationLabel: string;
  liveYearlyLabel: string;
  monthlyHint: string;
  monthlyUnit: string;
  confirmText: string;
  successText: string;
  errorText: string;
};

export type BiddingRoundTexts = {
  introTitle: string;
  introText: string;
  endedText: string;
  loginTitle: string;
  loginText: string;
  statsTitle: string;
  statsText: string;
  statsExplanation: string;
  statsTrafficLightSliderHint: string;
  statsSimpleLevelsSliderHint: string;
  pickupLocationTitle: string;
  pickupLocationText: string;
  summaryTitle: string;
  submitLabel: string;
  bid: BiddingRoundBidTexts;
};

export type BiddingRoundBidOptions = {
  quantityEnabled: boolean;
  multiplePositionsEnabled: boolean;
};

export type BiddingRoundPublicData = {
  enabled: boolean;
  urlEnabled: boolean;
  url?: string | null;
  displayName: string;
  round: BiddingRoundRound | null;
  roundStatus: "active" | "ended";
  texts: BiddingRoundTexts;
  biddableProduct: BiddingRoundProductType | null;
  pickupLocations: BiddingRoundPickupLocation[];
  bidOptions: BiddingRoundBidOptions;
  isAuthenticated: boolean;
  membershipIncludedInProductType?: boolean;
  currentPickupLocationId?: string | null;
  bid?: BiddingRoundBid | null;
};
