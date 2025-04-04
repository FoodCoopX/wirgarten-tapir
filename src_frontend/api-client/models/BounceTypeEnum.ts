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
 * * `soft` - Soft
 * * `hard` - Hard
 * * `unknown` - Unknown
 * * `not_analyzed` - Not analyzed
 * @export
 */
export const BounceTypeEnum = {
    Soft: 'soft',
    Hard: 'hard',
    Unknown: 'unknown',
    NotAnalyzed: 'not_analyzed'
} as const;
export type BounceTypeEnum = typeof BounceTypeEnum[keyof typeof BounceTypeEnum];


export function instanceOfBounceTypeEnum(value: any): boolean {
    for (const key in BounceTypeEnum) {
        if (Object.prototype.hasOwnProperty.call(BounceTypeEnum, key)) {
            if (BounceTypeEnum[key as keyof typeof BounceTypeEnum] === value) {
                return true;
            }
        }
    }
    return false;
}

export function BounceTypeEnumFromJSON(json: any): BounceTypeEnum {
    return BounceTypeEnumFromJSONTyped(json, false);
}

export function BounceTypeEnumFromJSONTyped(json: any, ignoreDiscriminator: boolean): BounceTypeEnum {
    return json as BounceTypeEnum;
}

export function BounceTypeEnumToJSON(value?: BounceTypeEnum | null): any {
    return value as any;
}

export function BounceTypeEnumToJSONTyped(value: any, ignoreDiscriminator: boolean): BounceTypeEnum {
    return value as BounceTypeEnum;
}

