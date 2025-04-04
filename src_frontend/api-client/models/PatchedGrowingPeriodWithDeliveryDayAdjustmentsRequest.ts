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
import type { DeliveryDayAdjustmentRequest } from './DeliveryDayAdjustmentRequest';
import {
    DeliveryDayAdjustmentRequestFromJSON,
    DeliveryDayAdjustmentRequestFromJSONTyped,
    DeliveryDayAdjustmentRequestToJSON,
    DeliveryDayAdjustmentRequestToJSONTyped,
} from './DeliveryDayAdjustmentRequest';

/**
 * 
 * @export
 * @interface PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest
 */
export interface PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest {
    /**
     * 
     * @type {string}
     * @memberof PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest
     */
    growingPeriodId?: string;
    /**
     * 
     * @type {Date}
     * @memberof PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest
     */
    growingPeriodStartDate?: Date;
    /**
     * 
     * @type {Date}
     * @memberof PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest
     */
    growingPeriodEndDate?: Date;
    /**
     * 
     * @type {Array<number>}
     * @memberof PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest
     */
    growingPeriodWeeksWithoutDelivery?: Array<number>;
    /**
     * 
     * @type {Array<DeliveryDayAdjustmentRequest>}
     * @memberof PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest
     */
    adjustments?: Array<DeliveryDayAdjustmentRequest>;
}

/**
 * Check if a given object implements the PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest interface.
 */
export function instanceOfPatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest(value: object): value is PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest {
    return true;
}

export function PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequestFromJSON(json: any): PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest {
    return PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequestFromJSONTyped(json, false);
}

export function PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequestFromJSONTyped(json: any, ignoreDiscriminator: boolean): PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest {
    if (json == null) {
        return json;
    }
    return {
        
        'growingPeriodId': json['growing_period_id'] == null ? undefined : json['growing_period_id'],
        'growingPeriodStartDate': json['growing_period_start_date'] == null ? undefined : (new Date(json['growing_period_start_date'])),
        'growingPeriodEndDate': json['growing_period_end_date'] == null ? undefined : (new Date(json['growing_period_end_date'])),
        'growingPeriodWeeksWithoutDelivery': json['growing_period_weeks_without_delivery'] == null ? undefined : json['growing_period_weeks_without_delivery'],
        'adjustments': json['adjustments'] == null ? undefined : ((json['adjustments'] as Array<any>).map(DeliveryDayAdjustmentRequestFromJSON)),
    };
}

  export function PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequestToJSON(json: any): PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest {
      return PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequestToJSONTyped(json, false);
  }

  export function PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequestToJSONTyped(value?: PatchedGrowingPeriodWithDeliveryDayAdjustmentsRequest | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'growing_period_id': value['growingPeriodId'],
        'growing_period_start_date': value['growingPeriodStartDate'] == null ? undefined : ((value['growingPeriodStartDate']).toISOString().substring(0,10)),
        'growing_period_end_date': value['growingPeriodEndDate'] == null ? undefined : ((value['growingPeriodEndDate']).toISOString().substring(0,10)),
        'growing_period_weeks_without_delivery': value['growingPeriodWeeksWithoutDelivery'],
        'adjustments': value['adjustments'] == null ? undefined : ((value['adjustments'] as Array<any>).map(DeliveryDayAdjustmentRequestToJSON)),
    };
}

