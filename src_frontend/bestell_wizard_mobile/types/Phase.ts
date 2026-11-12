type ProductTypeId = string & {};

export type Phase =
  | "loading"
  | "intro"
  | "pickup_location"
  | "solidarity"
  | "coop"
  | "personal_data"
  | "feedback"
  | "confirmation"
  | "unknown"
  | ProductTypeId;
