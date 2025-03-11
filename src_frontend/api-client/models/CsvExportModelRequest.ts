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
import type { AutomatedExportCycleEnum } from './AutomatedExportCycleEnum';
import {
    AutomatedExportCycleEnumFromJSON,
    AutomatedExportCycleEnumFromJSONTyped,
    AutomatedExportCycleEnumToJSON,
    AutomatedExportCycleEnumToJSONTyped,
} from './AutomatedExportCycleEnum';

/**
 * 
 * @export
 * @interface CsvExportModelRequest
 */
export interface CsvExportModelRequest {
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    id?: string;
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    exportSegmentId: string;
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    name: string;
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    description?: string;
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    separator: string;
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    fileName: string;
    /**
     * 
     * @type {Array<string>}
     * @memberof CsvExportModelRequest
     */
    columnIds?: Array<string>;
    /**
     * 
     * @type {Array<string>}
     * @memberof CsvExportModelRequest
     */
    emailRecipients?: Array<string>;
    /**
     * 
     * @type {AutomatedExportCycleEnum}
     * @memberof CsvExportModelRequest
     */
    automatedExportCycle: AutomatedExportCycleEnum;
    /**
     * 
     * @type {number}
     * @memberof CsvExportModelRequest
     */
    automatedExportDay: number;
    /**
     * 
     * @type {string}
     * @memberof CsvExportModelRequest
     */
    automatedExportHour: string;
}



/**
 * Check if a given object implements the CsvExportModelRequest interface.
 */
export function instanceOfCsvExportModelRequest(value: object): value is CsvExportModelRequest {
    if (!('exportSegmentId' in value) || value['exportSegmentId'] === undefined) return false;
    if (!('name' in value) || value['name'] === undefined) return false;
    if (!('separator' in value) || value['separator'] === undefined) return false;
    if (!('fileName' in value) || value['fileName'] === undefined) return false;
    if (!('automatedExportCycle' in value) || value['automatedExportCycle'] === undefined) return false;
    if (!('automatedExportDay' in value) || value['automatedExportDay'] === undefined) return false;
    if (!('automatedExportHour' in value) || value['automatedExportHour'] === undefined) return false;
    return true;
}

export function CsvExportModelRequestFromJSON(json: any): CsvExportModelRequest {
    return CsvExportModelRequestFromJSONTyped(json, false);
}

export function CsvExportModelRequestFromJSONTyped(json: any, ignoreDiscriminator: boolean): CsvExportModelRequest {
    if (json == null) {
        return json;
    }
    return {
        
        'id': json['id'] == null ? undefined : json['id'],
        'exportSegmentId': json['export_segment_id'],
        'name': json['name'],
        'description': json['description'] == null ? undefined : json['description'],
        'separator': json['separator'],
        'fileName': json['file_name'],
        'columnIds': json['column_ids'] == null ? undefined : json['column_ids'],
        'emailRecipients': json['email_recipients'] == null ? undefined : json['email_recipients'],
        'automatedExportCycle': AutomatedExportCycleEnumFromJSON(json['automated_export_cycle']),
        'automatedExportDay': json['automated_export_day'],
        'automatedExportHour': json['automated_export_hour'],
    };
}

  export function CsvExportModelRequestToJSON(json: any): CsvExportModelRequest {
      return CsvExportModelRequestToJSONTyped(json, false);
  }

  export function CsvExportModelRequestToJSONTyped(value?: CsvExportModelRequest | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'id': value['id'],
        'export_segment_id': value['exportSegmentId'],
        'name': value['name'],
        'description': value['description'],
        'separator': value['separator'],
        'file_name': value['fileName'],
        'column_ids': value['columnIds'],
        'email_recipients': value['emailRecipients'],
        'automated_export_cycle': AutomatedExportCycleEnumToJSON(value['automatedExportCycle']),
        'automated_export_day': value['automatedExportDay'],
        'automated_export_hour': value['automatedExportHour'],
    };
}

