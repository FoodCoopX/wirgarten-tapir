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


/**
 * * `picking_mode_basket` - Nach Kisten
 * * `picking_mode_share` - Nach Anteile
 * @export
 */
export const PickingModeEnum = {
    Basket: 'picking_mode_basket',
    Share: 'picking_mode_share'
} as const;
export type PickingModeEnum = typeof PickingModeEnum[keyof typeof PickingModeEnum];


export function instanceOfPickingModeEnum(value: any): boolean {
    for (const key in PickingModeEnum) {
        if (Object.prototype.hasOwnProperty.call(PickingModeEnum, key)) {
            if (PickingModeEnum[key as keyof typeof PickingModeEnum] === value) {
                return true;
            }
        }
    }
    return false;
}

export function PickingModeEnumFromJSON(json: any): PickingModeEnum {
    return PickingModeEnumFromJSONTyped(json, false);
}

export function PickingModeEnumFromJSONTyped(json: any, ignoreDiscriminator: boolean): PickingModeEnum {
    return json as PickingModeEnum;
}

export function PickingModeEnumToJSON(value?: PickingModeEnum | null): any {
    return value as any;
}

export function PickingModeEnumToJSONTyped(value: any, ignoreDiscriminator: boolean): PickingModeEnum {
    return value as PickingModeEnum;
}

