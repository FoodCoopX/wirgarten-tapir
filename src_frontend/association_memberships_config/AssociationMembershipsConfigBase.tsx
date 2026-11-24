import React, { useEffect, useState } from "react";
import { Alert, Card, Col, Row, Spinner } from "react-bootstrap";
import { AssociationMembershipType, AssociationsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import AssociationMembershipTypeCreateModal from "./AssociationMembershipTypeCreateModal.tsx";
import AssociationMembershipTypeTable from "./AssociationMembershipTypeTable.tsx";

interface AssociationMembershipsConfigProps {
  csrfToken: string;
}

const AssociationMembershipsConfigBase: React.FC<
  AssociationMembershipsConfigProps
> = ({ csrfToken }) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [membershipTypes, setMembershipTypes] = useState<
    AssociationMembershipType[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadMembershipTypes();
  }, []);

  function loadMembershipTypes() {
    setLoading(true);

    api
      .associationsAssociationMembershipTypesList()
      .then((types) => {
        setMembershipTypes(
          types.toSorted(
            (a, b) => a.orderInBestellWizard - b.orderInBestellWizard,
          ),
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vereinsmitgliedschafttypen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function getBody() {
    if (loading) {
      return <Spinner />;
    }

    if (membershipTypes.length === 0) {
      return (
        <Alert variant={"warning"}>
          Es muss mindestens 1 Mitgliedschafttyp geben. Lege ihn über
          „Mitgliedschafttyp erzeugen“ an.
        </Alert>
      );
    }

    const hasSupportingMembership = membershipTypes.some(
      (membershipType) => membershipType.isSupportingMembership,
    );

    return (
      <>
        <Alert variant={"info"}>
          Mitgliedschaftstypen, die als Fördermitgliedschaft gelten, mit „Ist
          Fördermitgliedschaft“ markieren. Sind bei der Rechtsform Verein Typen
          markiert, erscheinen ihre Namen im Bestell-Wizard auf Seite 3 und im
          Schritt Vereinsbeitritt wird nur dieser Typ angeboten. Ohne markierten
          Typ bzw. bei Genossenschaft greift der Text unter „Seite 3:
          Produktauswahl - Name für Fördermitgliedschaften“.
        </Alert>
        {!hasSupportingMembership && (
          <Alert variant={"warning"}>
            Kein Mitgliedschaftstyp ist als Fördermitgliedschaft markiert.
            Aktuell wird auf Seite 3 der Text unter „Seite 3: Produktauswahl -
            Name für Fördermitgliedschaften“ angezeigt und beim Vereinsbeitritt
            werden alle Typen angeboten.
          </Alert>
        )}
        <AssociationMembershipTypeTable
          membershipTypes={membershipTypes}
          setToastDatas={setToastDatas}
          csrfToken={csrfToken}
          loadData={loadMembershipTypes}
        />
      </>
    );
  }

  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={"d-flex justify-content-between align-items-center"}
              >
                <Card.Title className={"mb-0"}>Mitgliedschafttypen</Card.Title>
                <TapirButton
                  variant={"outline-primary"}
                  text={"Mitgliedschafttyp erzeugen"}
                  icon={"add_circle"}
                  onClick={() => setShowCreateModal(true)}
                />
              </div>
            </Card.Header>
            <Card.Body>{getBody()}</Card.Body>
          </Card>
        </Col>
      </Row>
      <AssociationMembershipTypeCreateModal
        csrfToken={csrfToken}
        show={showCreateModal}
        onHide={() => setShowCreateModal(false)}
        onCreated={() => {
          loadMembershipTypes();
          setShowCreateModal(false);
        }}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default AssociationMembershipsConfigBase;
