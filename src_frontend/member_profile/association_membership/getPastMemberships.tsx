import { AssociationMembership } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

export function getPastMemberships(memberships: AssociationMembership[]) {
  const today = new Date();
  const pastMemberships = memberships.filter(
    (membership) => membership.endDate && membership.endDate < today,
  );

  if (pastMemberships.length === 0) return undefined;

  return (
    <div>
      Vergangene Mitgliedschaften:{" "}
      <ul>
        {pastMemberships.map((membership) => (
          <li key={membership.id}>
            {membership.type.name} {formatDateNumeric(membership.startDate)}
            {" ➝ "}
            {formatDateNumeric(membership.endDate)}
          </li>
        ))}
      </ul>
    </div>
  );
}
