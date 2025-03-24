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


import * as runtime from '../runtime';
import type {
  Delivery,
  GrowingPeriod,
  GrowingPeriodRequest,
  MemberJokerInformation,
  PatchedGrowingPeriodRequest,
} from '../models/index';
import {
    DeliveryFromJSON,
    DeliveryToJSON,
    GrowingPeriodFromJSON,
    GrowingPeriodToJSON,
    GrowingPeriodRequestFromJSON,
    GrowingPeriodRequestToJSON,
    MemberJokerInformationFromJSON,
    MemberJokerInformationToJSON,
    PatchedGrowingPeriodRequestFromJSON,
    PatchedGrowingPeriodRequestToJSON,
} from '../models/index';

export interface DeliveriesApiCancelJokerCreateRequest {
    jokerId?: string;
}

export interface DeliveriesApiMemberDeliveriesListRequest {
    memberId?: string;
}

export interface DeliveriesApiMemberJokerInformationRetrieveRequest {
    memberId?: string;
}

export interface DeliveriesApiUseJokerCreateRequest {
    date?: Date;
    memberId?: string;
}

export interface DeliveriesGrowingPeriodsCreateRequest {
    growingPeriodRequest: GrowingPeriodRequest;
}

export interface DeliveriesGrowingPeriodsDestroyRequest {
    id: string;
}

export interface DeliveriesGrowingPeriodsPartialUpdateRequest {
    id: string;
    patchedGrowingPeriodRequest?: PatchedGrowingPeriodRequest;
}

export interface DeliveriesGrowingPeriodsRetrieveRequest {
    id: string;
}

export interface DeliveriesGrowingPeriodsUpdateRequest {
    id: string;
    growingPeriodRequest: GrowingPeriodRequest;
}

/**
 * 
 */
export class DeliveriesApi extends runtime.BaseAPI {

    /**
     */
    async deliveriesApiCancelJokerCreateRaw(requestParameters: DeliveriesApiCancelJokerCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<string>> {
        const queryParameters: any = {};

        if (requestParameters['jokerId'] != null) {
            queryParameters['joker_id'] = requestParameters['jokerId'];
        }

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/api/cancel_joker`,
            method: 'POST',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        if (this.isJsonMime(response.headers.get('content-type'))) {
            return new runtime.JSONApiResponse<string>(response);
        } else {
            return new runtime.TextApiResponse(response) as any;
        }
    }

    /**
     */
    async deliveriesApiCancelJokerCreate(requestParameters: DeliveriesApiCancelJokerCreateRequest = {}, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<string> {
        const response = await this.deliveriesApiCancelJokerCreateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesApiMemberDeliveriesListRaw(requestParameters: DeliveriesApiMemberDeliveriesListRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<Array<Delivery>>> {
        const queryParameters: any = {};

        if (requestParameters['memberId'] != null) {
            queryParameters['member_id'] = requestParameters['memberId'];
        }

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/api/member_deliveries`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => jsonValue.map(DeliveryFromJSON));
    }

    /**
     */
    async deliveriesApiMemberDeliveriesList(requestParameters: DeliveriesApiMemberDeliveriesListRequest = {}, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<Array<Delivery>> {
        const response = await this.deliveriesApiMemberDeliveriesListRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesApiMemberJokerInformationRetrieveRaw(requestParameters: DeliveriesApiMemberJokerInformationRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<MemberJokerInformation>> {
        const queryParameters: any = {};

        if (requestParameters['memberId'] != null) {
            queryParameters['member_id'] = requestParameters['memberId'];
        }

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/api/member_joker_information`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => MemberJokerInformationFromJSON(jsonValue));
    }

    /**
     */
    async deliveriesApiMemberJokerInformationRetrieve(requestParameters: DeliveriesApiMemberJokerInformationRetrieveRequest = {}, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<MemberJokerInformation> {
        const response = await this.deliveriesApiMemberJokerInformationRetrieveRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesApiUseJokerCreateRaw(requestParameters: DeliveriesApiUseJokerCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<string>> {
        const queryParameters: any = {};

        if (requestParameters['date'] != null) {
            queryParameters['date'] = (requestParameters['date'] as any).toISOString().substring(0,10);
        }

        if (requestParameters['memberId'] != null) {
            queryParameters['member_id'] = requestParameters['memberId'];
        }

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/api/use_joker`,
            method: 'POST',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        if (this.isJsonMime(response.headers.get('content-type'))) {
            return new runtime.JSONApiResponse<string>(response);
        } else {
            return new runtime.TextApiResponse(response) as any;
        }
    }

    /**
     */
    async deliveriesApiUseJokerCreate(requestParameters: DeliveriesApiUseJokerCreateRequest = {}, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<string> {
        const response = await this.deliveriesApiUseJokerCreateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesGrowingPeriodsCreateRaw(requestParameters: DeliveriesGrowingPeriodsCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<GrowingPeriod>> {
        if (requestParameters['growingPeriodRequest'] == null) {
            throw new runtime.RequiredError(
                'growingPeriodRequest',
                'Required parameter "growingPeriodRequest" was null or undefined when calling deliveriesGrowingPeriodsCreate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/deliveries/growing_periods/`,
            method: 'POST',
            headers: headerParameters,
            query: queryParameters,
            body: GrowingPeriodRequestToJSON(requestParameters['growingPeriodRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => GrowingPeriodFromJSON(jsonValue));
    }

    /**
     */
    async deliveriesGrowingPeriodsCreate(requestParameters: DeliveriesGrowingPeriodsCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<GrowingPeriod> {
        const response = await this.deliveriesGrowingPeriodsCreateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesGrowingPeriodsDestroyRaw(requestParameters: DeliveriesGrowingPeriodsDestroyRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<void>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling deliveriesGrowingPeriodsDestroy().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/growing_periods/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'DELETE',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.VoidApiResponse(response);
    }

    /**
     */
    async deliveriesGrowingPeriodsDestroy(requestParameters: DeliveriesGrowingPeriodsDestroyRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<void> {
        await this.deliveriesGrowingPeriodsDestroyRaw(requestParameters, initOverrides);
    }

    /**
     */
    async deliveriesGrowingPeriodsListRaw(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<Array<GrowingPeriod>>> {
        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/growing_periods/`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => jsonValue.map(GrowingPeriodFromJSON));
    }

    /**
     */
    async deliveriesGrowingPeriodsList(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<Array<GrowingPeriod>> {
        const response = await this.deliveriesGrowingPeriodsListRaw(initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesGrowingPeriodsPartialUpdateRaw(requestParameters: DeliveriesGrowingPeriodsPartialUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<GrowingPeriod>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling deliveriesGrowingPeriodsPartialUpdate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/deliveries/growing_periods/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'PATCH',
            headers: headerParameters,
            query: queryParameters,
            body: PatchedGrowingPeriodRequestToJSON(requestParameters['patchedGrowingPeriodRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => GrowingPeriodFromJSON(jsonValue));
    }

    /**
     */
    async deliveriesGrowingPeriodsPartialUpdate(requestParameters: DeliveriesGrowingPeriodsPartialUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<GrowingPeriod> {
        const response = await this.deliveriesGrowingPeriodsPartialUpdateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesGrowingPeriodsRetrieveRaw(requestParameters: DeliveriesGrowingPeriodsRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<GrowingPeriod>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling deliveriesGrowingPeriodsRetrieve().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/deliveries/growing_periods/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => GrowingPeriodFromJSON(jsonValue));
    }

    /**
     */
    async deliveriesGrowingPeriodsRetrieve(requestParameters: DeliveriesGrowingPeriodsRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<GrowingPeriod> {
        const response = await this.deliveriesGrowingPeriodsRetrieveRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async deliveriesGrowingPeriodsUpdateRaw(requestParameters: DeliveriesGrowingPeriodsUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<GrowingPeriod>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling deliveriesGrowingPeriodsUpdate().'
            );
        }

        if (requestParameters['growingPeriodRequest'] == null) {
            throw new runtime.RequiredError(
                'growingPeriodRequest',
                'Required parameter "growingPeriodRequest" was null or undefined when calling deliveriesGrowingPeriodsUpdate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/deliveries/growing_periods/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'PUT',
            headers: headerParameters,
            query: queryParameters,
            body: GrowingPeriodRequestToJSON(requestParameters['growingPeriodRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => GrowingPeriodFromJSON(jsonValue));
    }

    /**
     */
    async deliveriesGrowingPeriodsUpdate(requestParameters: DeliveriesGrowingPeriodsUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<GrowingPeriod> {
        const response = await this.deliveriesGrowingPeriodsUpdateRaw(requestParameters, initOverrides);
        return await response.value();
    }

}
