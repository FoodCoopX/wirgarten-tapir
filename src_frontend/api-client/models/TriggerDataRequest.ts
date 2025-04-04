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
 * @interface TriggerDataRequest
 */
export interface TriggerDataRequest {
    /**
     * 
     * @type {string}
     * @memberof TriggerDataRequest
     */
    triggerId: string;
    /**
     * 
     * @type {{ [key: string]: string; }}
     * @memberof TriggerDataRequest
     */
    triggerFieldValues: { [key: string]: string; };
}

/**
 * Check if a given object implements the TriggerDataRequest interface.
 */
export function instanceOfTriggerDataRequest(value: object): value is TriggerDataRequest {
    if (!('triggerId' in value) || value['triggerId'] === undefined) return false;
    if (!('triggerFieldValues' in value) || value['triggerFieldValues'] === undefined) return false;
    return true;
}

export function TriggerDataRequestFromJSON(json: any): TriggerDataRequest {
    return TriggerDataRequestFromJSONTyped(json, false);
}

export function TriggerDataRequestFromJSONTyped(json: any, ignoreDiscriminator: boolean): TriggerDataRequest {
    if (json == null) {
        return json;
    }
    return {
        
        'triggerId': json['trigger_id'],
        'triggerFieldValues': json['trigger_field_values'],
    };
}

  export function TriggerDataRequestToJSON(json: any): TriggerDataRequest {
      return TriggerDataRequestToJSONTyped(json, false);
  }

  export function TriggerDataRequestToJSONTyped(value?: TriggerDataRequest | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'trigger_id': value['triggerId'],
        'trigger_field_values': value['triggerFieldValues'],
    };
}

