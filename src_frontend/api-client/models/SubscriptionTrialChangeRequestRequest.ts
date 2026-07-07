/* tslint:disable */
/* eslint-disable */

export interface SubscriptionTrialChangeRequestRequest {
  subscriptionId: string;
  trialDisabled: boolean;
  trialEndDateOverride?: Date | null;
}

export function SubscriptionTrialChangeRequestRequestToJSON(
  value?: SubscriptionTrialChangeRequestRequest | null,
): any {
  if (value == null) {
    return value;
  }

  return {
    subscription_id: value.subscriptionId,
    trial_disabled: value.trialDisabled,
    trial_end_date_override:
      value.trialEndDateOverride == null
        ? null
        : [
            value.trialEndDateOverride.getFullYear(),
            String(value.trialEndDateOverride.getMonth() + 1).padStart(2, "0"),
            String(value.trialEndDateOverride.getDate()).padStart(2, "0"),
          ].join("-"),
  };
}
