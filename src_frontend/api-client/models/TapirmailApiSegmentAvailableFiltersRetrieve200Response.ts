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
 * @interface TapirmailApiSegmentAvailableFiltersRetrieve200Response
 */
export interface TapirmailApiSegmentAvailableFiltersRetrieve200Response {
    /**
     * 
     * @type {Array<string>}
     * @memberof TapirmailApiSegmentAvailableFiltersRetrieve200Response
     */
    filters?: Array<string>;
}

/**
 * Check if a given object implements the TapirmailApiSegmentAvailableFiltersRetrieve200Response interface.
 */
export function instanceOfTapirmailApiSegmentAvailableFiltersRetrieve200Response(value: object): value is TapirmailApiSegmentAvailableFiltersRetrieve200Response {
    return true;
}

export function TapirmailApiSegmentAvailableFiltersRetrieve200ResponseFromJSON(json: any): TapirmailApiSegmentAvailableFiltersRetrieve200Response {
    return TapirmailApiSegmentAvailableFiltersRetrieve200ResponseFromJSONTyped(json, false);
}

export function TapirmailApiSegmentAvailableFiltersRetrieve200ResponseFromJSONTyped(json: any, ignoreDiscriminator: boolean): TapirmailApiSegmentAvailableFiltersRetrieve200Response {
    if (json == null) {
        return json;
    }
    return {
        
        'filters': json['filters'] == null ? undefined : json['filters'],
    };
}

  export function TapirmailApiSegmentAvailableFiltersRetrieve200ResponseToJSON(json: any): TapirmailApiSegmentAvailableFiltersRetrieve200Response {
      return TapirmailApiSegmentAvailableFiltersRetrieve200ResponseToJSONTyped(json, false);
  }

  export function TapirmailApiSegmentAvailableFiltersRetrieve200ResponseToJSONTyped(value?: TapirmailApiSegmentAvailableFiltersRetrieve200Response | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'filters': value['filters'],
    };
}

