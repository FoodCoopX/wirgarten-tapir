import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import { type AssociationMembership, AssociationsApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { getCurrentMembership } from "./getCurrentMembership.tsx";
import { getFutureMemberships } from "./getFutureMemberships.tsx";
import { getPastMemberships } from "./getPastMemberships.tsx";

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
  const [orderWizardUrl, setOrderWizardUrl] = useState<string>();

  useEffect(() => {
    loadData();
  }, [memberId]);

  function loadData() {
    setLoading(true);

    api
      .associationsApiMemberAssociationMembershipsRetrieve({
        memberId: memberId,
      })
      .then((response) => {
        setMemberships(response.memberships);
        setOrderWizardUrl(response.orderWizardUrl ?? undefined);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vereinsmitgliedschaften",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Card className={"mb-2"}>
        <Card.Header>
          <div className={"d-flex justify-content-between align-items-center"}>
            <Card.Title className={"mb-0"}>Vereinsmitgliedschaft</Card.Title>
          </div>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <Spinner />
          ) : (
            <>
              {memberships.length === 0 ? (
                "Keine Mitgliedschaft"
              ) : (
                <>
                  {getCurrentMembership(memberships)}
                  {getFutureMemberships(memberships)}
                  {getPastMemberships(memberships)}
                </>
              )}
            </>
          )}
        </Card.Body>
        {orderWizardUrl && (
          <Card.Footer>
            <div className={"d-flex justify-content-end"}>
              <TapirButton
                variant={"outline-primary"}
                icon={"add"}
                onClick={() => location.assign(orderWizardUrl)}
              />
            </div>
          </Card.Footer>
        )}
      </Card>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default AssociationMembershipCard;
