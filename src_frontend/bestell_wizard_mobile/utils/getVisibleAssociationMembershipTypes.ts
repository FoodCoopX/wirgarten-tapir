import { AssociationMembershipType } from "../../api-client";

export function getVisibleAssociationMembershipTypes(
  associationMembershipTypes: AssociationMembershipType[],
) {
  return associationMembershipTypes.filter(
    (membershipType) => !membershipType.hiddenInBestellWizard,
  );
}
