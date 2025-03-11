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
 * @interface ExportSegmentColumnRequest
 */
export interface ExportSegmentColumnRequest {
    /**
     * 
     * @type {string}
     * @memberof ExportSegmentColumnRequest
     */
    id: string;
    /**
     * 
     * @type {string}
     * @memberof ExportSegmentColumnRequest
     */
    displayName: string;
    /**
     * 
     * @type {string}
     * @memberof ExportSegmentColumnRequest
     */
    description: string;
}

/**
 * Check if a given object implements the ExportSegmentColumnRequest interface.
 */
export function instanceOfExportSegmentColumnRequest(value: object): value is ExportSegmentColumnRequest {
    if (!('id' in value) || value['id'] === undefined) return false;
    if (!('displayName' in value) || value['displayName'] === undefined) return false;
    if (!('description' in value) || value['description'] === undefined) return false;
    return true;
}

export function ExportSegmentColumnRequestFromJSON(json: any): ExportSegmentColumnRequest {
    return ExportSegmentColumnRequestFromJSONTyped(json, false);
}

export function ExportSegmentColumnRequestFromJSONTyped(json: any, ignoreDiscriminator: boolean): ExportSegmentColumnRequest {
    if (json == null) {
        return json;
    }
    return {
        
        'id': json['id'],
        'displayName': json['display_name'],
        'description': json['description'],
    };
}

  export function ExportSegmentColumnRequestToJSON(json: any): ExportSegmentColumnRequest {
      return ExportSegmentColumnRequestToJSONTyped(json, false);
  }

  export function ExportSegmentColumnRequestToJSONTyped(value?: ExportSegmentColumnRequest | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'id': value['id'],
        'display_name': value['displayName'],
        'description': value['description'],
    };
}

