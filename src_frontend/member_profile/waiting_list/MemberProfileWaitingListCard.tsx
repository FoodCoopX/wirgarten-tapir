import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Card, Col, Row, Spinner } from "react-bootstrap";
import { WaitingListApi, WaitingListEntryDetails } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface MemberProfileWaitingListCardProps {
  memberId: string;
  adminEmail: string;
}

const MemberProfileWaitingListCard: React.FC<
  MemberProfileWaitingListCardProps
> = ({ memberId, adminEmail }) => {
  const [waitingListEntry, setWaitingListEntry] =
    useState<WaitingListEntryDetails>();
  const [loading, setLoading] = useState(true);
  const api = useApi(WaitingListApi, "unused");

  useEffect(() => {
    setLoading(true);
    api
      .waitingListApiMemberWaitingListEntryDetailsRetrieve({
        memberId: memberId,
      })
      .then((result) => {
        setWaitingListEntry(result.entry);
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Laden des Wartelisteneintrags.",
        );
      })
      .finally(() => setLoading(false));
  }, [memberId]);

  function buildContent() {
    if (loading)
      return (
        <Card>
          <Card.Header>
            <h5 className={"mb-0"}>Wartelisteneintrag</h5>
          </Card.Header>
          <Card.Body>
            <Spinner />
          </Card.Body>
        </Card>
      );

    if (waitingListEntry === undefined) return null;

    return (
      <Card>
        <Card.Header>
          <h5 className={"mb-0"}>Wartelisteneintrag</h5>
        </Card.Header>
        <Card.Body>
          <Row>
            <p>Du stehst mit folgenden Wünschen auf der Warteliste:</p>
          </Row>
          <Row>
            {waitingListEntry.pickupLocationWishes &&
              waitingListEntry.pickupLocationWishes.length > 0 && (
                <Col>
                  Verteilstationswünsche
                  <ol>
                    {waitingListEntry.pickupLocationWishes
                      .sort((w1, w2) => w1.priority - w2.priority)
                      .map((wish) => (
                        <li key={wish.id!}>{wish.pickupLocation.name}</li>
                      ))}
                  </ol>
                </Col>
              )}
            {waitingListEntry.productWishes &&
              waitingListEntry.productWishes.length > 0 && (
                <Col>
                  Produktwünsche
                  <ul>
                    {waitingListEntry.productWishes.map((wish) => (
                      <li key={wish.id}>
                        {wish.product.name} {"×"} {wish.quantity}
                      </li>
                    ))}
                  </ul>
                </Col>
              )}
          </Row>
          {waitingListEntry.numberOfCoopShares > 0 && (
            <Row>
              {waitingListEntry.numberOfCoopShares}{" "}
              {waitingListEntry.numberOfCoopShares === 1
                ? "Genossenschaftsanteil"
                : "Genossenschaftsanteile"}
            </Row>
          )}
          <Row>
            <p>
              Möchtest du deine Wartelisteneinträge verändern, dann wende dich
              bitte an <a href={"mailto:" + adminEmail}>{adminEmail}</a>.
            </p>
          </Row>
        </Card.Body>
      </Card>
    );
  }
  return buildContent();
};

export default MemberProfileWaitingListCard;
