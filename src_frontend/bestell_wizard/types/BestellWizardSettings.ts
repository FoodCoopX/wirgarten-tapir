import { TapirTheme } from "../../types/TapirTheme.ts";
import {
  BestellWizardImages,
  BestellWizardStrings,
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
  distributionChannels: string[];
  solidarityContributionChoices: string[];
  solidarityContributionMinimum: number | null;
  feedbackStepEnabled: boolean;
  strings: BestellWizardStrings;
  images: BestellWizardImages;
};
