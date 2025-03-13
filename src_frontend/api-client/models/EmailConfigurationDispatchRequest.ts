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
import type { EmailConfigurationVersionRequest } from './EmailConfigurationVersionRequest';
import {
    EmailConfigurationVersionRequestFromJSON,
    EmailConfigurationVersionRequestFromJSONTyped,
    EmailConfigurationVersionRequestToJSON,
    EmailConfigurationVersionRequestToJSONTyped,
} from './EmailConfigurationVersionRequest';

/**
 * 
 * @export
 * @interface EmailConfigurationDispatchRequest
 */
export interface EmailConfigurationDispatchRequest {
    /**
     * 
     * @type {string}
     * @memberof EmailConfigurationDispatchRequest
     */
    id: string;
    /**
     * 
     * @type {EmailConfigurationVersionRequest}
     * @memberof EmailConfigurationDispatchRequest
     */
    emailConfigurationVersion: EmailConfigurationVersionRequest;
    /**
     * 
     * @type {Date}
     * @memberof EmailConfigurationDispatchRequest
     */
    scheduledTime: Date;
    /**
     * 
     * @type {{ [key: string]: any; }}
     * @memberof EmailConfigurationDispatchRequest
     */
    overrideRecipients: { [key: string]: any; };
}

/**
 * Check if a given object implements the EmailConfigurationDispatchRequest interface.
 */
export function instanceOfEmailConfigurationDispatchRequest(value: object): value is EmailConfigurationDispatchRequest {
    if (!('id' in value) || value['id'] === undefined) return false;
    if (!('emailConfigurationVersion' in value) || value['emailConfigurationVersion'] === undefined) return false;
    if (!('scheduledTime' in value) || value['scheduledTime'] === undefined) return false;
    if (!('overrideRecipients' in value) || value['overrideRecipients'] === undefined) return false;
    return true;
}

export function EmailConfigurationDispatchRequestFromJSON(json: any): EmailConfigurationDispatchRequest {
    return EmailConfigurationDispatchRequestFromJSONTyped(json, false);
}

export function EmailConfigurationDispatchRequestFromJSONTyped(json: any, ignoreDiscriminator: boolean): EmailConfigurationDispatchRequest {
    if (json == null) {
        return json;
    }
    return {
        
        'id': json['id'],
        'emailConfigurationVersion': EmailConfigurationVersionRequestFromJSON(json['email_configuration_version']),
        'scheduledTime': (new Date(json['scheduled_time'])),
        'overrideRecipients': json['override_recipients'],
    };
}

  export function EmailConfigurationDispatchRequestToJSON(json: any): EmailConfigurationDispatchRequest {
      return EmailConfigurationDispatchRequestToJSONTyped(json, false);
  }

  export function EmailConfigurationDispatchRequestToJSONTyped(value?: EmailConfigurationDispatchRequest | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'id': value['id'],
        'email_configuration_version': EmailConfigurationVersionRequestToJSON(value['emailConfigurationVersion']),
        'scheduled_time': ((value['scheduledTime']).toISOString()),
        'override_recipients': value['overrideRecipients'],
    };
}

