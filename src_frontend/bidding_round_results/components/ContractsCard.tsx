import React from "react";
import { Alert, Button, Card, Form } from "react-bootstrap";

import { BiddingRoundsApi } from "../../api-client/apis/BiddingRoundsApi.ts";
import { Round } from "../../api-client/models/Round.ts";
import { RoundResultsResponse } from "../../api-client/models/RoundResultsResponse.ts";

interface ContractsCardProps {
  round: Round;
  results: RoundResultsResponse;
  isLocked: boolean;
  busy: boolean;
  createAutoRenewed: boolean;
  setCreateAutoRenewed: React.Dispatch<React.SetStateAction<boolean>>;
  api: BiddingRoundsApi;
  roundId: string;
  runAction: (action: () => Promise<unknown>, message: string) => Promise<void>;
}

const ContractsCard: React.FC<ContractsCardProps> = ({
  round,
  results,
  isLocked,
  busy,
  createAutoRenewed,
  setCreateAutoRenewed,
  api,
  roundId,
  runAction,
}) => {
  let content: React.ReactNode;
  if (round.contractsCreatedAt) {
    content = (
      <Alert variant={"success"}>
        Verträge erstellt am{" "}
        {new Date(round.contractsCreatedAt).toLocaleString("de-DE")}. Die
        Erzeugung ist endgültig; Korrekturen laufen über die normalen
        Verwaltungswerkzeuge.
      </Alert>
    );
  } else if (round.status !== "closed") {
    content = (
      <Alert variant={"info"}>
        Verträge können erst erstellt werden, wenn die Beitragsrunde geschlossen
        ist.
      </Alert>
    );
  } else if (!isLocked) {
    content = (
      <Alert variant={"warning"}>
        Bitte zuerst das Durchschnittsgebot fixieren.
      </Alert>
    );
  } else if (results.unconfirmedBidCount > 0) {
    content = (
      <Alert variant={"warning"}>
        Es gibt noch {results.unconfirmedBidCount} unbestätigte Gebote.
      </Alert>
    );
  } else {
    content = (
      <>
        <Form.Check
          type={"checkbox"}
          className={"mb-3"}
          label={"Verträge für automatisch verlängerte Mitglieder mit erzeugen"}
          checked={createAutoRenewed}
          onChange={(event) => setCreateAutoRenewed(event.target.checked)}
        />
        <Button
          variant={"dark"}
          disabled={busy || results.bids.length === 0}
          onClick={() =>
            runAction(
              () =>
                api.biddingRoundsApiCreateContractsCreate({
                  roundId,
                  createContractsRequest: {
                    createAutoRenewedContracts: createAutoRenewed,
                  },
                }),
              "Verträge erstellt",
            )
          }
        >
          Verträge aus allen Geboten erstellen
        </Button>
      </>
    );
  }

  return (
    <Card>
      <Card.Header>
        <strong>Verträge</strong>
      </Card.Header>
      <Card.Body>{content}</Card.Body>
    </Card>
  );
};

export default ContractsCard;
