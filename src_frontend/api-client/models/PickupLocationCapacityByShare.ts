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
 * @interface PickupLocationCapacityByShare
 */
export interface PickupLocationCapacityByShare {
    /**
     * 
     * @type {string}
     * @memberof PickupLocationCapacityByShare
     */
    productTypeName: string;
    /**
     * 
     * @type {string}
     * @memberof PickupLocationCapacityByShare
     */
    productTypeId: string;
    /**
     * 
     * @type {number}
     * @memberof PickupLocationCapacityByShare
     */
    capacity?: number;
}

/**
 * Check if a given object implements the PickupLocationCapacityByShare interface.
 */
export function instanceOfPickupLocationCapacityByShare(value: object): value is PickupLocationCapacityByShare {
    if (!('productTypeName' in value) || value['productTypeName'] === undefined) return false;
    if (!('productTypeId' in value) || value['productTypeId'] === undefined) return false;
    return true;
}

export function PickupLocationCapacityByShareFromJSON(json: any): PickupLocationCapacityByShare {
    return PickupLocationCapacityByShareFromJSONTyped(json, false);
}

export function PickupLocationCapacityByShareFromJSONTyped(json: any, ignoreDiscriminator: boolean): PickupLocationCapacityByShare {
    if (json == null) {
        return json;
    }
    return {
        
        'productTypeName': json['product_type_name'],
        'productTypeId': json['product_type_id'],
        'capacity': json['capacity'] == null ? undefined : json['capacity'],
    };
}

  export function PickupLocationCapacityByShareToJSON(json: any): PickupLocationCapacityByShare {
      return PickupLocationCapacityByShareToJSONTyped(json, false);
  }

  export function PickupLocationCapacityByShareToJSONTyped(value?: PickupLocationCapacityByShare | null, ignoreDiscriminator: boolean = false): any {
    if (value == null) {
        return value;
    }

    return {
        
        'product_type_name': value['productTypeName'],
        'product_type_id': value['productTypeId'],
        'capacity': value['capacity'],
    };
}

