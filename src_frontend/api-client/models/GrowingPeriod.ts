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
 * @interface GrowingPeriod
 */
export interface GrowingPeriod {
    /**
     * 
     * @type {string}
     * @memberof GrowingPeriod
     */
    id?: string;
    /**
     * 
     * @type {Date}
     * @memberof GrowingPeriod
     */
    startDate: Date;
    /**
     * 
     * @type {Date}
     * @memberof GrowingPeriod
     */
    endDate: Date;
    /**
     * 
     * @type {Array<number>}
     * @memberof GrowingPeriod
     */
    weeksWithoutDelivery?: Array<number>;
}

/**
 * Check if a given object implements the GrowingPeriod interface.
 */
export function instanceOfGrowingPeriod(value: object): value is GrowingPeriod {
    if (!('startDate' in value) || value['startDate'] === undefined) return false;
    if (!('endDate' in value) || value['endDate'] === undefined) return false;
    return true;
}

export function GrowingPeriodFromJSON(json: any): GrowingPeriod {
    return GrowingPeriodFromJSONTyped(json, false);
}

export function GrowingPeriodFromJSONTyped(json: any, ignoreDiscriminator: boolean): GrowingPeriod {
    if (json == null) {
        return json;
    }
    return {
        
        'id': json['id'] == null ? undefined : json['id'],
        'startDate': (new Date(json['start_date'])),
        'endDate': (new Date(json['end_date'])),
        'weeksWithoutDelivery': json['weeks_without_delivery'] == null ? undefined : json['weeks_without_delivery'],
    };
}

  export function GrowingPeriodToJSON(json: any): GrowingPeriod {
      return GrowingPeriodToJSONTyped(json, false);
  }

  export function GrowingPeriodToJSONTyped(value?: GrowingPeriod | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'id': value['id'],
        'start_date': ((value['startDate']).toISOString().substring(0,10)),
        'end_date': ((value['endDate']).toISOString().substring(0,10)),
        'weeks_without_delivery': value['weeksWithoutDelivery'],
    };
}

