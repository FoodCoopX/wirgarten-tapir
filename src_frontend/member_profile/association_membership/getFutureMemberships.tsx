import { AssociationMembership } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

export function getFutureMemberships(memberships: AssociationMembership[]) {
  const today = new Date();
  const futureMemberships = memberships.filter(
    (membership) => membership.startDate > today,
  );

  if (futureMemberships.length === 0) return undefined;

  return (
    <div>
      Zukünftige Mitgliedschaften:{" "}
      <ul>
        {futureMemberships.map((membership) => (
          <li key={membership.id}>
            {membership.type.name} ab dem{" "}
            {formatDateNumeric(membership.startDate)}
            {membership.endDate && (
              <span> bis zum {formatDateNumeric(membership.endDate)}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
