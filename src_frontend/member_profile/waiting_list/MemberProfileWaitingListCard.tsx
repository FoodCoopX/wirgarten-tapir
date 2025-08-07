import React, { useEffect, useState } from "react";
import { Card, Col, Row, Spinner } from "react-bootstrap";
import "dayjs/locale/de";
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
          "Fehler beim Laden der Warteliste-Eintrag.",
        );
      })
      .finally(() => setLoading(false));
  }, [memberId]);

  function buildContent() {
    if (loading) return <Spinner />;

    if (waitingListEntry === undefined) return null;

    return (
      <Card>
        <Card.Header>
          <h5 className={"mb-0"}>Warteliste-Eintrag</h5>
        </Card.Header>
        <Card.Body>
          <Row>
            <p>Du stehst gerade auf der Warteliste mit folgende Wünsche:</p>
          </Row>
          <Row>
            {waitingListEntry.pickupLocationWishes &&
              waitingListEntry.pickupLocationWishes.length > 0 && (
                <Col>
                  Verteilstation-Wünsche
                  <ol>
                    {waitingListEntry.pickupLocationWishes
                      .sort((w1, w2) => w1.priority - w2.priority)
                      .map((wish) => (
                        <li>{wish.pickupLocation.name}</li>
                      ))}
                  </ol>
                </Col>
              )}
            {waitingListEntry.productWishes &&
              waitingListEntry.productWishes.length > 0 && (
                <Col>
                  Produkt-Wünsche
                  <ul>
                    {waitingListEntry.productWishes.map((wish) => (
                      <li>
                        {wish.product.name} {"×"} {wish.quantity}
                      </li>
                    ))}
                  </ul>
                </Col>
              )}
          </Row>
          {waitingListEntry.numberOfCoopShares > 0 && (
            <Row>
              {waitingListEntry.numberOfCoopShares} Genossenschaftsanteile
            </Row>
          )}
          <Row>
            <p>
              Möchtest du deine Wartelisteneinträge verändern, dann wende dich
              bitte an <a href={"mailto:" + adminEmail}>{adminEmail}</a>
            </p>
          </Row>
        </Card.Body>
      </Card>
    );
  }
  return buildContent();
};

export default MemberProfileWaitingListCard;
