import { TapirTheme } from "../../types/TapirTheme.ts";
import {
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
  strings: BestellWizardStrings;
};
