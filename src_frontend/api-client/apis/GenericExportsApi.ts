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
  BuildExportResponse,
  CsvExportModel,
  CsvExportModelRequest,
  ExportSegment,
  PatchedCsvExportModelRequest,
  PatchedPdfExportModelRequest,
  PdfExportModel,
  PdfExportModelRequest,
} from '../models/index';
import {
    BuildExportResponseFromJSON,
    BuildExportResponseToJSON,
    CsvExportModelFromJSON,
    CsvExportModelToJSON,
    CsvExportModelRequestFromJSON,
    CsvExportModelRequestToJSON,
    ExportSegmentFromJSON,
    ExportSegmentToJSON,
    PatchedCsvExportModelRequestFromJSON,
    PatchedCsvExportModelRequestToJSON,
    PatchedPdfExportModelRequestFromJSON,
    PatchedPdfExportModelRequestToJSON,
    PdfExportModelFromJSON,
    PdfExportModelToJSON,
    PdfExportModelRequestFromJSON,
    PdfExportModelRequestToJSON,
} from '../models/index';

export interface GenericExportsBuildCsvExportRetrieveRequest {
    csvExportId?: string;
    referenceDatetime?: Date;
}

export interface GenericExportsBuildPdfExportRetrieveRequest {
    pdfExportId?: string;
    referenceDatetime?: Date;
}

export interface GenericExportsCsvExportsCreateRequest {
    csvExportModelRequest: CsvExportModelRequest;
}

export interface GenericExportsCsvExportsDestroyRequest {
    id: string;
}

export interface GenericExportsCsvExportsPartialUpdateRequest {
    id: string;
    patchedCsvExportModelRequest?: PatchedCsvExportModelRequest;
}

export interface GenericExportsCsvExportsRetrieveRequest {
    id: string;
}

export interface GenericExportsCsvExportsUpdateRequest {
    id: string;
    csvExportModelRequest: CsvExportModelRequest;
}

export interface GenericExportsPdfExportsCreateRequest {
    pdfExportModelRequest: PdfExportModelRequest;
}

export interface GenericExportsPdfExportsDestroyRequest {
    id: string;
}

export interface GenericExportsPdfExportsPartialUpdateRequest {
    id: string;
    patchedPdfExportModelRequest?: PatchedPdfExportModelRequest;
}

export interface GenericExportsPdfExportsRetrieveRequest {
    id: string;
}

export interface GenericExportsPdfExportsUpdateRequest {
    id: string;
    pdfExportModelRequest: PdfExportModelRequest;
}

/**
 * 
 */
export class GenericExportsApi extends runtime.BaseAPI {

    /**
     */
    async genericExportsBuildCsvExportRetrieveRaw(requestParameters: GenericExportsBuildCsvExportRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<BuildExportResponse>> {
        const queryParameters: any = {};

        if (requestParameters['csvExportId'] != null) {
            queryParameters['csv_export_id'] = requestParameters['csvExportId'];
        }

        if (requestParameters['referenceDatetime'] != null) {
            queryParameters['reference_datetime'] = (requestParameters['referenceDatetime'] as any).toISOString();
        }

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/build_csv_export`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => BuildExportResponseFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsBuildCsvExportRetrieve(requestParameters: GenericExportsBuildCsvExportRetrieveRequest = {}, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<BuildExportResponse> {
        const response = await this.genericExportsBuildCsvExportRetrieveRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsBuildPdfExportRetrieveRaw(requestParameters: GenericExportsBuildPdfExportRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<BuildExportResponse>> {
        const queryParameters: any = {};

        if (requestParameters['pdfExportId'] != null) {
            queryParameters['pdf_export_id'] = requestParameters['pdfExportId'];
        }

        if (requestParameters['referenceDatetime'] != null) {
            queryParameters['reference_datetime'] = (requestParameters['referenceDatetime'] as any).toISOString();
        }

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/build_pdf_export`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => BuildExportResponseFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsBuildPdfExportRetrieve(requestParameters: GenericExportsBuildPdfExportRetrieveRequest = {}, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<BuildExportResponse> {
        const response = await this.genericExportsBuildPdfExportRetrieveRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsCsvExportsCreateRaw(requestParameters: GenericExportsCsvExportsCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<CsvExportModel>> {
        if (requestParameters['csvExportModelRequest'] == null) {
            throw new runtime.RequiredError(
                'csvExportModelRequest',
                'Required parameter "csvExportModelRequest" was null or undefined when calling genericExportsCsvExportsCreate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/generic_exports/csv_exports/`,
            method: 'POST',
            headers: headerParameters,
            query: queryParameters,
            body: CsvExportModelRequestToJSON(requestParameters['csvExportModelRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => CsvExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsCsvExportsCreate(requestParameters: GenericExportsCsvExportsCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<CsvExportModel> {
        const response = await this.genericExportsCsvExportsCreateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsCsvExportsDestroyRaw(requestParameters: GenericExportsCsvExportsDestroyRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<void>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsCsvExportsDestroy().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/csv_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'DELETE',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.VoidApiResponse(response);
    }

    /**
     */
    async genericExportsCsvExportsDestroy(requestParameters: GenericExportsCsvExportsDestroyRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<void> {
        await this.genericExportsCsvExportsDestroyRaw(requestParameters, initOverrides);
    }

    /**
     */
    async genericExportsCsvExportsListRaw(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<Array<CsvExportModel>>> {
        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/csv_exports/`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => jsonValue.map(CsvExportModelFromJSON));
    }

    /**
     */
    async genericExportsCsvExportsList(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<Array<CsvExportModel>> {
        const response = await this.genericExportsCsvExportsListRaw(initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsCsvExportsPartialUpdateRaw(requestParameters: GenericExportsCsvExportsPartialUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<CsvExportModel>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsCsvExportsPartialUpdate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/generic_exports/csv_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'PATCH',
            headers: headerParameters,
            query: queryParameters,
            body: PatchedCsvExportModelRequestToJSON(requestParameters['patchedCsvExportModelRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => CsvExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsCsvExportsPartialUpdate(requestParameters: GenericExportsCsvExportsPartialUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<CsvExportModel> {
        const response = await this.genericExportsCsvExportsPartialUpdateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsCsvExportsRetrieveRaw(requestParameters: GenericExportsCsvExportsRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<CsvExportModel>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsCsvExportsRetrieve().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/csv_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => CsvExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsCsvExportsRetrieve(requestParameters: GenericExportsCsvExportsRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<CsvExportModel> {
        const response = await this.genericExportsCsvExportsRetrieveRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsCsvExportsUpdateRaw(requestParameters: GenericExportsCsvExportsUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<CsvExportModel>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsCsvExportsUpdate().'
            );
        }

        if (requestParameters['csvExportModelRequest'] == null) {
            throw new runtime.RequiredError(
                'csvExportModelRequest',
                'Required parameter "csvExportModelRequest" was null or undefined when calling genericExportsCsvExportsUpdate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/generic_exports/csv_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'PUT',
            headers: headerParameters,
            query: queryParameters,
            body: CsvExportModelRequestToJSON(requestParameters['csvExportModelRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => CsvExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsCsvExportsUpdate(requestParameters: GenericExportsCsvExportsUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<CsvExportModel> {
        const response = await this.genericExportsCsvExportsUpdateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsExportSegmentsListRaw(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<Array<ExportSegment>>> {
        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/export_segments`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => jsonValue.map(ExportSegmentFromJSON));
    }

    /**
     */
    async genericExportsExportSegmentsList(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<Array<ExportSegment>> {
        const response = await this.genericExportsExportSegmentsListRaw(initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsPdfExportsCreateRaw(requestParameters: GenericExportsPdfExportsCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<PdfExportModel>> {
        if (requestParameters['pdfExportModelRequest'] == null) {
            throw new runtime.RequiredError(
                'pdfExportModelRequest',
                'Required parameter "pdfExportModelRequest" was null or undefined when calling genericExportsPdfExportsCreate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/generic_exports/pdf_exports/`,
            method: 'POST',
            headers: headerParameters,
            query: queryParameters,
            body: PdfExportModelRequestToJSON(requestParameters['pdfExportModelRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => PdfExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsPdfExportsCreate(requestParameters: GenericExportsPdfExportsCreateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<PdfExportModel> {
        const response = await this.genericExportsPdfExportsCreateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsPdfExportsDestroyRaw(requestParameters: GenericExportsPdfExportsDestroyRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<void>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsPdfExportsDestroy().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/pdf_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'DELETE',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.VoidApiResponse(response);
    }

    /**
     */
    async genericExportsPdfExportsDestroy(requestParameters: GenericExportsPdfExportsDestroyRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<void> {
        await this.genericExportsPdfExportsDestroyRaw(requestParameters, initOverrides);
    }

    /**
     */
    async genericExportsPdfExportsListRaw(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<Array<PdfExportModel>>> {
        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/pdf_exports/`,
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => jsonValue.map(PdfExportModelFromJSON));
    }

    /**
     */
    async genericExportsPdfExportsList(initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<Array<PdfExportModel>> {
        const response = await this.genericExportsPdfExportsListRaw(initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsPdfExportsPartialUpdateRaw(requestParameters: GenericExportsPdfExportsPartialUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<PdfExportModel>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsPdfExportsPartialUpdate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/generic_exports/pdf_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'PATCH',
            headers: headerParameters,
            query: queryParameters,
            body: PatchedPdfExportModelRequestToJSON(requestParameters['patchedPdfExportModelRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => PdfExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsPdfExportsPartialUpdate(requestParameters: GenericExportsPdfExportsPartialUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<PdfExportModel> {
        const response = await this.genericExportsPdfExportsPartialUpdateRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsPdfExportsRetrieveRaw(requestParameters: GenericExportsPdfExportsRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<PdfExportModel>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsPdfExportsRetrieve().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        const response = await this.request({
            path: `/generic_exports/pdf_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'GET',
            headers: headerParameters,
            query: queryParameters,
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => PdfExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsPdfExportsRetrieve(requestParameters: GenericExportsPdfExportsRetrieveRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<PdfExportModel> {
        const response = await this.genericExportsPdfExportsRetrieveRaw(requestParameters, initOverrides);
        return await response.value();
    }

    /**
     */
    async genericExportsPdfExportsUpdateRaw(requestParameters: GenericExportsPdfExportsUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<runtime.ApiResponse<PdfExportModel>> {
        if (requestParameters['id'] == null) {
            throw new runtime.RequiredError(
                'id',
                'Required parameter "id" was null or undefined when calling genericExportsPdfExportsUpdate().'
            );
        }

        if (requestParameters['pdfExportModelRequest'] == null) {
            throw new runtime.RequiredError(
                'pdfExportModelRequest',
                'Required parameter "pdfExportModelRequest" was null or undefined when calling genericExportsPdfExportsUpdate().'
            );
        }

        const queryParameters: any = {};

        const headerParameters: runtime.HTTPHeaders = {};

        headerParameters['Content-Type'] = 'application/json';

        const response = await this.request({
            path: `/generic_exports/pdf_exports/{id}/`.replace(`{${"id"}}`, encodeURIComponent(String(requestParameters['id']))),
            method: 'PUT',
            headers: headerParameters,
            query: queryParameters,
            body: PdfExportModelRequestToJSON(requestParameters['pdfExportModelRequest']),
        }, initOverrides);

        return new runtime.JSONApiResponse(response, (jsonValue) => PdfExportModelFromJSON(jsonValue));
    }

    /**
     */
    async genericExportsPdfExportsUpdate(requestParameters: GenericExportsPdfExportsUpdateRequest, initOverrides?: RequestInit | runtime.InitOverrideFunction): Promise<PdfExportModel> {
        const response = await this.genericExportsPdfExportsUpdateRaw(requestParameters, initOverrides);
        return await response.value();
    }

}
