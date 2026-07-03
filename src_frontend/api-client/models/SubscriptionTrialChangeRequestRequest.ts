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
        : value.trialEndDateOverride.toISOString().substring(0, 10),
  };
}
