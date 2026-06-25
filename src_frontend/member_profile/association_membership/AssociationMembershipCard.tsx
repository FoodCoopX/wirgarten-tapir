import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import { type AssociationMembership, AssociationsApi } from "../../api-client";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface AssociationMembershipCardProps {
  memberId: string;
  csrfToken: string;
}

const AssociationMembershipCard: React.FC<AssociationMembershipCardProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [memberships, setMemberships] = useState<AssociationMembership[]>([]);

  useEffect(() => {
    setLoading(true);

    api
      .associationsApiMemberAssociationMembershipsList({ memberId: memberId })
      .then(setMemberships)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vereinsmitgliedschaften",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [memberId]);

  function getCurrentMembership() {
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

  function getFutureMemberships() {
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

  function getPastMemberships() {
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

  return (
    <>
      <Card className={"mb-2"}>
        <Card.Header>
          <Card.Title>Vereinsmitgliedschaft</Card.Title>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <Spinner />
          ) : (
            <>
              {getCurrentMembership()}
              {getFutureMemberships()}
              {getPastMemberships()}
            </>
          )}
        </Card.Body>
      </Card>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default AssociationMembershipCard;
