import { TapirTheme } from "../../types/TapirTheme.ts";
import {
  BestellWizardImages,
  BestellWizardStrings,
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
} from "../../api-client";

export type BestellWizardSettings = {
  theme: TapirTheme;
  pickupLocations: PublicPickupLocation[];
  productTypes: PublicProductType[];
  priceOfAShare: number;
  allowInvestingMembership: boolean;
  forceWaitingList: boolean;
  showCoopContent: boolean;
  introStepText: string;
  labelCheckboxSepaMandat: string;
  labelCheckboxContractPolicy: string;
  revocationRightsExplanation: string;
  trialPeriodLengthInWeeks: number;
  paymentRhythmChoices: { [key: string]: string };
  studentStatusAllowed: boolean;
  introEnabled: boolean;
  productTypeIdsThatAreAlreadyAtCapacity: string[];
  productIdsThatAreAlreadyAtCapacity: string[];
  coopStatuteLink: string;
  organizationName: string;
  logoUrl: string;
  contactMailAddress: string;
  distributionChannels: { [key: string]: string };
  solidarityContributionChoices: string[];
  solidarityContributionMinimum: number | null;
  solidarityContributionDefault: number;
  feedbackStepEnabled: boolean;
  growingPeriodChoices: PublicGrowingPeriod[];
  strings: BestellWizardStrings;
  images: BestellWizardImages;
  debug: boolean;
};
