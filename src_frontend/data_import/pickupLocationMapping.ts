import {
  Column,
  DataImportPickupLocation,
  UploadResponse,
} from "../api-client";

const normalize = (value: string) =>
  value.trim().replace(/\s+/g, " ").toLowerCase();

export function defaultPickupTarget(
  value: string,
  pickupLocations: DataImportPickupLocation[],
  createMissing: boolean,
): string {
  const existing = pickupLocations.find(
    (location) => normalize(location.name) === normalize(value),
  );
  if (existing) return `existing:${existing.id}`;
  return createMissing ? "create" : "skip";
}

export function pickupColumnValues(
  upload: UploadResponse,
  mapping: Record<number, string>,
) {
  const pickupColumn = upload.columns.find(
    (column: Column) => mapping[column.index] === "members:Abholort",
  );
  return upload.distinctValues.find(
    (column) => column.header === pickupColumn?.header,
  );
}

export function effectivePickupMapping(
  upload: UploadResponse,
  mapping: Record<number, string>,
  pickupMapping: Record<string, string>,
  createMissing: boolean,
): { value: string; target: string }[] {
  const distinct = pickupColumnValues(upload, mapping);
  if (!distinct || distinct.capped) return [];
  return distinct.values.map(({ value }) => ({
    value,
    target:
      pickupMapping[value] ??
      defaultPickupTarget(value, upload.pickupLocations, createMissing),
  }));
}
