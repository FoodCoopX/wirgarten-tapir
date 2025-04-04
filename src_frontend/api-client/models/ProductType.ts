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
import type { DeliveryCycleEnum } from './DeliveryCycleEnum';
import {
    DeliveryCycleEnumFromJSON,
    DeliveryCycleEnumFromJSONTyped,
    DeliveryCycleEnumToJSON,
    DeliveryCycleEnumToJSONTyped,
} from './DeliveryCycleEnum';

/**
 * 
 * @export
 * @interface ProductType
 */
export interface ProductType {
    /**
     * 
     * @type {string}
     * @memberof ProductType
     */
    id?: string;
    /**
     * 
     * @type {string}
     * @memberof ProductType
     */
    name: string;
    /**
     * 
     * @type {DeliveryCycleEnum}
     * @memberof ProductType
     */
    deliveryCycle?: DeliveryCycleEnum;
    /**
     * 
     * @type {string}
     * @memberof ProductType
     */
    contractLink?: string | null;
    /**
     * 
     * @type {string}
     * @memberof ProductType
     */
    iconLink?: string | null;
    /**
     * 
     * @type {boolean}
     * @memberof ProductType
     */
    singleSubscriptionOnly?: boolean;
    /**
     * 
     * @type {boolean}
     * @memberof ProductType
     */
    isAffectedByJokers?: boolean;
}



/**
 * Check if a given object implements the ProductType interface.
 */
export function instanceOfProductType(value: object): value is ProductType {
    if (!('name' in value) || value['name'] === undefined) return false;
    return true;
}

export function ProductTypeFromJSON(json: any): ProductType {
    return ProductTypeFromJSONTyped(json, false);
}

export function ProductTypeFromJSONTyped(json: any, ignoreDiscriminator: boolean): ProductType {
    if (json == null) {
        return json;
    }
    return {
        
        'id': json['id'] == null ? undefined : json['id'],
        'name': json['name'],
        'deliveryCycle': json['delivery_cycle'] == null ? undefined : DeliveryCycleEnumFromJSON(json['delivery_cycle']),
        'contractLink': json['contract_link'] == null ? undefined : json['contract_link'],
        'iconLink': json['icon_link'] == null ? undefined : json['icon_link'],
        'singleSubscriptionOnly': json['single_subscription_only'] == null ? undefined : json['single_subscription_only'],
        'isAffectedByJokers': json['is_affected_by_jokers'] == null ? undefined : json['is_affected_by_jokers'],
    };
}

  export function ProductTypeToJSON(json: any): ProductType {
      return ProductTypeToJSONTyped(json, false);
  }

  export function ProductTypeToJSONTyped(value?: ProductType | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'id': value['id'],
        'name': value['name'],
        'delivery_cycle': DeliveryCycleEnumToJSON(value['deliveryCycle']),
        'contract_link': value['contractLink'],
        'icon_link': value['iconLink'],
        'single_subscription_only': value['singleSubscriptionOnly'],
        'is_affected_by_jokers': value['isAffectedByJokers'],
    };
}

