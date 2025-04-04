/* tslint:disable */
/* eslint-disable */
/**
 * 
 * No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)
 *
 * The version of the OpenAPI document: 0.0.0
 * 
 *
 * NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).
 * https://openapi-generator.tech
 * Do not edit the class manually.
 */

import { mapValues } from '../runtime';
/**
 * 
 * @export
 * @interface CancelSubscriptionsViewResponse
 */
export interface CancelSubscriptionsViewResponse {
    /**
     * 
     * @type {boolean}
     * @memberof CancelSubscriptionsViewResponse
     */
    subscriptionsCancelled: boolean;
    /**
     * 
     * @type {Array<string>}
     * @memberof CancelSubscriptionsViewResponse
     */
    errors: Array<string>;
}

/**
 * Check if a given object implements the CancelSubscriptionsViewResponse interface.
 */
export function instanceOfCancelSubscriptionsViewResponse(value: object): value is CancelSubscriptionsViewResponse {
    if (!('subscriptionsCancelled' in value) || value['subscriptionsCancelled'] === undefined) return false;
    if (!('errors' in value) || value['errors'] === undefined) return false;
    return true;
}

export function CancelSubscriptionsViewResponseFromJSON(json: any): CancelSubscriptionsViewResponse {
    return CancelSubscriptionsViewResponseFromJSONTyped(json, false);
}

export function CancelSubscriptionsViewResponseFromJSONTyped(json: any, ignoreDiscriminator: boolean): CancelSubscriptionsViewResponse {
    if (json == null) {
        return json;
    }
    return {
        
        'subscriptionsCancelled': json['subscriptions_cancelled'],
        'errors': json['errors'],
    };
}

  export function CancelSubscriptionsViewResponseToJSON(json: any): CancelSubscriptionsViewResponse {
      return CancelSubscriptionsViewResponseToJSONTyped(json, false);
  }

  export function CancelSubscriptionsViewResponseToJSONTyped(value?: CancelSubscriptionsViewResponse | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'subscriptions_cancelled': value['subscriptionsCancelled'],
        'errors': value['errors'],
    };
}

