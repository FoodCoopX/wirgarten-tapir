import { Card } from "react-bootstrap";
import TapirButton from "../components/TapirButton";
export default function DataImportActivationCard({
  count,
  onSend,
  loading,
}: {
  count: number;
  onSend: () => void;
  loading: boolean;
}) {
  return (
    <Card className="mb-3">
      <Card.Header>Logins für übernommene Mitglieder</Card.Header>
      <Card.Body>
        <p>
          {count} Mitglieder mit Anteilen oder laufendem Vertrag haben noch
          keinen Login. Sie bekommen einen Login und eine Mail, mit der sie ihr
          Passwort setzen. Erst verschicken, wenn Mitglieder, Anteile und
          Verträge übernommen sind.
        </p>
        {count > 0 && (
          <TapirButton
            variant="primary"
            text="Aktivierungsmails verschicken"
            icon="mail"
            onClick={onSend}
            loading={loading}
          />
        )}
      </Card.Body>
    </Card>
  );
}
