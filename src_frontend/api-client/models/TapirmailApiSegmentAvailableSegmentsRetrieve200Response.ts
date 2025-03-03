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
 * @interface TapirmailApiSegmentAvailableSegmentsRetrieve200Response
 */
export interface TapirmailApiSegmentAvailableSegmentsRetrieve200Response {
    /**
     * 
     * @type {Array<string>}
     * @memberof TapirmailApiSegmentAvailableSegmentsRetrieve200Response
     */
    segments?: Array<string>;
    /**
     * 
     * @type {Array<string>}
     * @memberof TapirmailApiSegmentAvailableSegmentsRetrieve200Response
     */
    staticSegments?: Array<string>;
}

/**
 * Check if a given object implements the TapirmailApiSegmentAvailableSegmentsRetrieve200Response interface.
 */
export function instanceOfTapirmailApiSegmentAvailableSegmentsRetrieve200Response(value: object): value is TapirmailApiSegmentAvailableSegmentsRetrieve200Response {
    return true;
}

export function TapirmailApiSegmentAvailableSegmentsRetrieve200ResponseFromJSON(json: any): TapirmailApiSegmentAvailableSegmentsRetrieve200Response {
    return TapirmailApiSegmentAvailableSegmentsRetrieve200ResponseFromJSONTyped(json, false);
}

export function TapirmailApiSegmentAvailableSegmentsRetrieve200ResponseFromJSONTyped(json: any, ignoreDiscriminator: boolean): TapirmailApiSegmentAvailableSegmentsRetrieve200Response {
    if (json == null) {
        return json;
    }
    return {
        
        'segments': json['segments'] == null ? undefined : json['segments'],
        'staticSegments': json['staticSegments'] == null ? undefined : json['staticSegments'],
    };
}

  export function TapirmailApiSegmentAvailableSegmentsRetrieve200ResponseToJSON(json: any): TapirmailApiSegmentAvailableSegmentsRetrieve200Response {
      return TapirmailApiSegmentAvailableSegmentsRetrieve200ResponseToJSONTyped(json, false);
  }

  export function TapirmailApiSegmentAvailableSegmentsRetrieve200ResponseToJSONTyped(value?: TapirmailApiSegmentAvailableSegmentsRetrieve200Response | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'segments': value['segments'],
        'staticSegments': value['staticSegments'],
    };
}

