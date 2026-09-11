import { AssociationMembership } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

export function getCurrentMembership(memberships: AssociationMembership[]) {
  const today = new Date();
  const membership = memberships.find(
    (membership) =>
      membership.startDate < today &&
      (!membership.endDate || membership.endDate >= today),
  );

  if (!membership) return undefined;

  return (
    <div>
      Aktuelle Mitgliedschaft:{" "}
      <ul>
        <li>
          {membership.type.name} seit dem{" "}
          {formatDateNumeric(membership.startDate)}{" "}
          {membership.endDate && (
            <span>, endet am {formatDateNumeric(membership.endDate)}</span>
          )}
        </li>
      </ul>
    </div>
  );
}
