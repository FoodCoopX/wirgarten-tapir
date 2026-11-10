import {
  DayOfWeekEnum,
  PickupLocation,
  PickupLocationSaveRequestRequest,
} from "../api-client";

export const WEEKDAYS = [
  "Montag",
  "Dienstag",
  "Mittwoch",
  "Donnerstag",
  "Freitag",
  "Samstag",
  "Sonntag",
];

export interface FormState {
  name: string;
  coordsLat: string;
  coordsLon: string;
  street: string;
  street2: string;
  postcode: string;
  city: string;
  locationRouteId: string;
  accessCode: string;
  messengerGroupLink: string;
  contactName: string;
  photoLink: string;
  showDetailsInBasketTotalsExport: boolean;
  info: string;
  routeInfo: string;
  startDate: string;
  endDate: string;
}

export interface OpeningTimeRow {
  dayOfWeek: DayOfWeekEnum;
  openTime: string;
  closeTime: string;
}

export const API_KEYS: Record<keyof FormState, string> = {
  name: "name",
  coordsLat: "coords_lat",
  coordsLon: "coords_lon",
  street: "street",
  street2: "street_2",
  postcode: "postcode",
  city: "city",
  locationRouteId: "location_route_id",
  accessCode: "access_code",
  messengerGroupLink: "messenger_group_link",
  contactName: "contact_name",
  photoLink: "photo_link",
  showDetailsInBasketTotalsExport: "show_details_in_basket_totals_export",
  info: "info",
  routeInfo: "route_info",
  startDate: "start_date",
  endDate: "end_date",
};
export const OPENING_TIMES_API_KEY = "opening_times";

export const EMPTY_FORM: FormState = {
  name: "",
  coordsLat: "",
  coordsLon: "",
  street: "",
  street2: "",
  postcode: "",
  city: "",
  locationRouteId: "",
  accessCode: "",
  messengerGroupLink: "",
  contactName: "",
  photoLink: "",
  showDetailsInBasketTotalsExport: false,
  info: "",
  routeInfo: "",
  startDate: "",
  endDate: "",
};

function dateToInputValue(date: Date | null | undefined) {
  return date ? date.toISOString().substring(0, 10) : "";
}

export function buildFormState(pickupLocation: PickupLocation): FormState {
  return {
    name: pickupLocation.name,
    coordsLat: pickupLocation.coordsLat,
    coordsLon: pickupLocation.coordsLon,
    street: pickupLocation.street,
    street2: pickupLocation.street2 ?? "",
    postcode: pickupLocation.postcode,
    city: pickupLocation.city,
    locationRouteId: pickupLocation.locationRoute ?? "",
    accessCode: pickupLocation.accessCode ?? "",
    messengerGroupLink: pickupLocation.messengerGroupLink ?? "",
    contactName: pickupLocation.contactName ?? "",
    photoLink: pickupLocation.photoLink ?? "",
    showDetailsInBasketTotalsExport:
      pickupLocation.showDetailsInBasketTotalsExport ?? false,
    info: pickupLocation.info ?? "",
    routeInfo: pickupLocation.routeInfo ?? "",
    startDate: dateToInputValue(pickupLocation.startDate),
    endDate: dateToInputValue(pickupLocation.endDate),
  };
}

export function buildRequest(
  form: FormState,
  openingTimes: OpeningTimeRow[],
): PickupLocationSaveRequestRequest {
  return {
    ...form,
    locationRouteId: form.locationRouteId || null,
    startDate: form.startDate ? new Date(form.startDate) : null,
    endDate: form.endDate ? new Date(form.endDate) : null,
    openingTimes: sortOpeningTimes(openingTimes),
  };
}

export function sortOpeningTimes(openingTimes: OpeningTimeRow[]) {
  return [...openingTimes].sort(
    (a, b) => a.dayOfWeek - b.dayOfWeek || a.openTime.localeCompare(b.openTime),
  );
}

export function getWeekdayIndex(date: string) {
  return (new Date(date).getUTCDay() + 6) % 7;
}

export function getDateErrors(form: FormState): Record<string, string> {
  const errors: Record<string, string> = {};
  if (form.startDate && getWeekdayIndex(form.startDate) !== 0) {
    errors["start_date"] =
      `${WEEKDAYS[getWeekdayIndex(form.startDate)]} gewählt: Verteilstationen können nur an einem Montag geöffnet werden.`;
  }
  if (form.endDate && getWeekdayIndex(form.endDate) !== 6) {
    errors["end_date"] =
      `${WEEKDAYS[getWeekdayIndex(form.endDate)]} gewählt: Verteilstationen können nur an einem Sonntag geschlossen werden.`;
  } else if (form.startDate && form.endDate && form.endDate < form.startDate) {
    errors["end_date"] = "Ende darf nicht vor Beginn liegen.";
  }
  return errors;
}
