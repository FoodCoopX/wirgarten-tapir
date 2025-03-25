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
import type { DeliveryDayAdjustment } from './DeliveryDayAdjustment';
import {
    DeliveryDayAdjustmentFromJSON,
    DeliveryDayAdjustmentFromJSONTyped,
    DeliveryDayAdjustmentToJSON,
    DeliveryDayAdjustmentToJSONTyped,
} from './DeliveryDayAdjustment';
import type { GrowingPeriod } from './GrowingPeriod';
import {
    GrowingPeriodFromJSON,
    GrowingPeriodFromJSONTyped,
    GrowingPeriodToJSON,
    GrowingPeriodToJSONTyped,
} from './GrowingPeriod';

/**
 * 
 * @export
 * @interface GrowingPeriodWithDeliveryDayAdjustments
 */
export interface GrowingPeriodWithDeliveryDayAdjustments {
    /**
     * 
     * @type {GrowingPeriod}
     * @memberof GrowingPeriodWithDeliveryDayAdjustments
     */
    growingPeriod: GrowingPeriod;
    /**
     * 
     * @type {Array<DeliveryDayAdjustment>}
     * @memberof GrowingPeriodWithDeliveryDayAdjustments
     */
    adjustments: Array<DeliveryDayAdjustment>;
}

/**
 * Check if a given object implements the GrowingPeriodWithDeliveryDayAdjustments interface.
 */
export function instanceOfGrowingPeriodWithDeliveryDayAdjustments(value: object): value is GrowingPeriodWithDeliveryDayAdjustments {
    if (!('growingPeriod' in value) || value['growingPeriod'] === undefined) return false;
    if (!('adjustments' in value) || value['adjustments'] === undefined) return false;
    return true;
}

export function GrowingPeriodWithDeliveryDayAdjustmentsFromJSON(json: any): GrowingPeriodWithDeliveryDayAdjustments {
    return GrowingPeriodWithDeliveryDayAdjustmentsFromJSONTyped(json, false);
}

export function GrowingPeriodWithDeliveryDayAdjustmentsFromJSONTyped(json: any, ignoreDiscriminator: boolean): GrowingPeriodWithDeliveryDayAdjustments {
    if (json == null) {
        return json;
    }
    return {
        
        'growingPeriod': GrowingPeriodFromJSON(json['growing_period']),
        'adjustments': ((json['adjustments'] as Array<any>).map(DeliveryDayAdjustmentFromJSON)),
    };
}

  export function GrowingPeriodWithDeliveryDayAdjustmentsToJSON(json: any): GrowingPeriodWithDeliveryDayAdjustments {
      return GrowingPeriodWithDeliveryDayAdjustmentsToJSONTyped(json, false);
  }

  export function GrowingPeriodWithDeliveryDayAdjustmentsToJSONTyped(value?: GrowingPeriodWithDeliveryDayAdjustments | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'growing_period': GrowingPeriodToJSON(value['growingPeriod']),
        'adjustments': ((value['adjustments'] as Array<any>).map(DeliveryDayAdjustmentToJSON)),
    };
}

