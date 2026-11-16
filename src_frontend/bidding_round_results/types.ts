import type { ChartData } from "chart.js";

import type { AutoRenewedMember } from "../api-client/models/AutoRenewedMember.ts";
import type { Bid } from "../api-client/models/Bid.ts";
import type { BidAdminItemRequest } from "../api-client/models/BidAdminItemRequest.ts";
import type { BidItem } from "../api-client/models/BidItem.ts";
import type { ContractRow } from "../api-client/models/ContractRow.ts";
import type { CreateContractsError } from "../api-client/models/CreateContractsError.ts";
import type { ResultsTable } from "../api-client/models/ResultsTable.ts";
import type { ResultsTableMember } from "../api-client/models/ResultsTableMember.ts";
import type { ResultsTablePickupLocation } from "../api-client/models/ResultsTablePickupLocation.ts";
import type { RoundResultsResponse } from "../api-client/models/RoundResultsResponse.ts";
import type { RoundStatsEntry } from "../api-client/models/RoundStatsEntry.ts";

// View-model types of the evaluation page, derived from the generated client
// models. The aliases keep the component interfaces readable.
export type BiddingRoundResultsResponse = RoundResultsResponse;
export type BiddingRoundResultsTable = ResultsTable;
export type BiddingRoundMemberRow = ResultsTableMember;
export type BiddingRoundPickupFillRow = ResultsTablePickupLocation;
export type BiddingRoundStatsRow = RoundStatsEntry;
export type BiddingRoundAutoRenewedRow = AutoRenewedMember;
export type BiddingRoundContractRow = ContractRow;
export type BiddingRoundBid = Bid;
export type BiddingRoundBidItem = BidItem;
export type ContractCreationError = CreateContractsError;

/**
 * Editable bid item of the admin modal. The API transports the amounts as
 * strings; the form keeps them as controlled input values and converts them
 * back into a request payload on save.
 */
export interface BidItemDraft {
  roundProductTypeId: string;
  productId: string;
  quantity: number;
  amount1?: string | null;
  amount2?: string | null;
  amount3?: string | null;
}

/** Item payload of the admin bid endpoints (`create` and `partial_update`). */
export type BidItemPayload = BidAdminItemRequest;

/** Values collected by the bid modal and sent to the admin bid endpoints. */
export interface BidFormPayload {
  memberId: string;
  items: BidItemPayload[];
  enteredByAdmin: boolean;
}

/** Member preselected when the bid modal opens from the results table. */
export interface BidMemberSelection {
  memberId: string;
  memberName: string;
}

/** Open/closed state of the collapsible sections. */
export interface BiddingRoundSections {
  pickupLocations: boolean;
  bids: boolean;
  contracts: boolean;
}

/** Slider position at which the current members cover the target. */
export interface CoverageTarget {
  position: number;
  targetCovered: boolean;
}

/** One line of the 12-month balance chart. */
export interface TwelveMonthSeries {
  label: string;
  color: string;
  data: number[];
}

/** Derived data of the 12-month projection. */
export interface TwelveMonthProjection {
  openShares: number;
  breakEvenMonth: number | null;
  saldoAfterTwelveMonths: number;
  chartData: ChartData<"bar">;
}
