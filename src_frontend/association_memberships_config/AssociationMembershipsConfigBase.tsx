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
      .then(setMembershipTypes)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vereinsmitgliedschafsttypen",
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
          Es muss mindestens 1 Mitgliedschafttyp geben
        </Alert>
      );
    }

    return (
      <AssociationMembershipTypeTable
        membershipTypes={membershipTypes}
        setToastDatas={setToastDatas}
        csrfToken={csrfToken}
        loadData={loadMembershipTypes}
      />
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
