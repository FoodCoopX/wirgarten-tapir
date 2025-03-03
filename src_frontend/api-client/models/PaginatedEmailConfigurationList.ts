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
import type { EmailConfiguration } from './EmailConfiguration';
import {
    EmailConfigurationFromJSON,
    EmailConfigurationFromJSONTyped,
    EmailConfigurationToJSON,
    EmailConfigurationToJSONTyped,
} from './EmailConfiguration';

/**
 * 
 * @export
 * @interface PaginatedEmailConfigurationList
 */
export interface PaginatedEmailConfigurationList {
    /**
     * 
     * @type {number}
     * @memberof PaginatedEmailConfigurationList
     */
    count: number;
    /**
     * 
     * @type {string}
     * @memberof PaginatedEmailConfigurationList
     */
    next?: string | null;
    /**
     * 
     * @type {string}
     * @memberof PaginatedEmailConfigurationList
     */
    previous?: string | null;
    /**
     * 
     * @type {Array<EmailConfiguration>}
     * @memberof PaginatedEmailConfigurationList
     */
    results: Array<EmailConfiguration>;
}

/**
 * Check if a given object implements the PaginatedEmailConfigurationList interface.
 */
export function instanceOfPaginatedEmailConfigurationList(value: object): value is PaginatedEmailConfigurationList {
    if (!('count' in value) || value['count'] === undefined) return false;
    if (!('results' in value) || value['results'] === undefined) return false;
    return true;
}

export function PaginatedEmailConfigurationListFromJSON(json: any): PaginatedEmailConfigurationList {
    return PaginatedEmailConfigurationListFromJSONTyped(json, false);
}

export function PaginatedEmailConfigurationListFromJSONTyped(json: any, ignoreDiscriminator: boolean): PaginatedEmailConfigurationList {
    if (json == null) {
        return json;
    }
    return {
        
        'count': json['count'],
        'next': json['next'] == null ? undefined : json['next'],
        'previous': json['previous'] == null ? undefined : json['previous'],
        'results': ((json['results'] as Array<any>).map(EmailConfigurationFromJSON)),
    };
}

  export function PaginatedEmailConfigurationListToJSON(json: any): PaginatedEmailConfigurationList {
      return PaginatedEmailConfigurationListToJSONTyped(json, false);
  }

  export function PaginatedEmailConfigurationListToJSONTyped(value?: PaginatedEmailConfigurationList | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'count': value['count'],
        'next': value['next'],
        'previous': value['previous'],
        'results': ((value['results'] as Array<any>).map(EmailConfigurationToJSON)),
    };
}

