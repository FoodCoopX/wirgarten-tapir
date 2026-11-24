import { AssociationMembershipType } from "../../api-client";
import { getVisibleAssociationMembershipTypes } from "./getVisibleAssociationMembershipTypes.ts";

export function getDisplayedAssociationMembershipTypes(
  associationMembershipTypes: AssociationMembershipType[],
  investingMembership: boolean,
): AssociationMembershipType[] {
  const visibleTypes = getVisibleAssociationMembershipTypes(
    associationMembershipTypes,
  );

  if (!investingMembership) {
    return visibleTypes;
  }

  const supportingTypes = visibleTypes.filter(
    (type) => type.isSupportingMembership,
  );

  return supportingTypes.length > 0 ? supportingTypes : visibleTypes;
}
