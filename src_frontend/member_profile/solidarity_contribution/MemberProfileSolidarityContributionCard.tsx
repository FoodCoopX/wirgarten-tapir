import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import "dayjs/locale/de";
import {
  SolidarityContribution,
  SolidarityContributionApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";

interface MemberProfileSolidarityContributionCardProps {
  memberId: string;
  adminEmail: string;
}

const MemberProfileSolidarityContributionCard: React.FC<
  MemberProfileSolidarityContributionCardProps
> = ({ memberId, adminEmail }) => {
  const [loading, setLoading] = useState(true);
  const api = useApi(SolidarityContributionApi, "unused");
  const [solidarityContributions, setSolidarityContributions] = useState<
    SolidarityContribution[]
  >([]);

  useEffect(() => {
    setLoading(true);

    api
      .solidarityContributionApiMemberSolidarityContributionsList({
        memberId: memberId,
      })
      .then(setSolidarityContributions)
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Laden der Solidarbeitrag.",
        );
      })
      .finally(() => setLoading(false));
  }, [memberId]);

  function getCurrentContribution() {
    for (const contribution of solidarityContributions) {
      const today = new Date();
      if (contribution.startDate < today && today < contribution.endDate) {
        return contribution;
      }
    }
  }

  function buildCurrentContribution() {
    const contribution = getCurrentContribution();
    const amount = contribution
      ? formatCurrency(parseFloat(contribution.amount))
      : "Kein Beitrag";

    return "Aktueller Beitrag: " + amount;
  }

  function buildFutureContributions() {
    const today = new Date();
    const futureContributions = solidarityContributions.filter(
      (contribution) => contribution.startDate > today,
    );

    if (futureContributions.length === 0) {
      return;
    }

    return futureContributions.map((contribution) => (
      <>
        <br />
        <span>
          Ab dem {formatDateNumeric(contribution.startDate)}:{" "}
          {formatCurrency(parseFloat(contribution.amount))}
        </span>
      </>
    ));
  }

  function buildContent() {
    if (loading)
      return (
        <Card>
          <Card.Header>
            <h5 className={"mb-0"}>Solidarbeitrag</h5>
          </Card.Header>
          <Card.Body>
            <Spinner />
          </Card.Body>
        </Card>
      );

    return (
      <Card>
        <Card.Header>
          <h5 className={"mb-0"}>Solidarbeitrag</h5>
        </Card.Header>
        <Card.Body>
          {buildCurrentContribution()}
          {buildFutureContributions()}
        </Card.Body>
      </Card>
    );
  }
  return buildContent();
};

export default MemberProfileSolidarityContributionCard;
