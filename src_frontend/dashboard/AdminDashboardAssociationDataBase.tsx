import React, { useId, useState } from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import AssociationMembershipChart from "./AssociationMembershipChart.tsx";

interface AdminDashboardAssociationDataBaseProps {
  csrfToken: string;
}

const AdminDashboardAssociationDataBase: React.FC<
  AdminDashboardAssociationDataBaseProps
> = ({ csrfToken }) => {
  const titleId = useId();
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <div className={"d-flex gap-2"}>
        <TapirButton
          icon={"bar_chart"}
          variant={"outline-secondary"}
          text={"Mitgliedschaftsstatistik"}
          onClick={() => setShowModal(true)}
        />
      </div>
      {showModal && (
        <Modal
          show={showModal}
          onHide={() => setShowModal(false)}
          size={"xl"}
          scrollable
          aria-labelledby={titleId}
        >
          <Modal.Header closeButton closeLabel={"Schließen"}>
            <Modal.Title id={titleId}>Mitgliedschaftsstatistik</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <div className={"d-flex gap-2 flex-column"}>
              <AssociationMembershipChart
                csrfToken={csrfToken}
                title="Aktive Vereinsmitgliedschaften"
                chartType="line"
                loadData="associationsApiNumberOfAssociationMembersPerMonthRetrieve"
                errorMessage="Fehler beim Laden der Mitgliederzahlen"
              />
              <AssociationMembershipChart
                csrfToken={csrfToken}
                title="Mitgliedschaftsenden nach Monat"
                chartType="bar"
                loadData="associationsApiNumberOfAssociationMembershipCancellationsPerMonthRetrieve"
                errorMessage="Fehler beim Laden der Mitgliedschaftsenden"
              />
              <AssociationMembershipChart
                csrfToken={csrfToken}
                title="Erfasste Kündigungen nach Monat"
                chartType="bar"
                loadData="associationsApiNumberOfAssociationMembershipCancellationsPerMonthRelativeToCancellationRetrieve"
                errorMessage="Fehler beim Laden der erfassten Kündigungen"
              />
            </div>
          </Modal.Body>
        </Modal>
      )}
    </>
  );
};

export default AdminDashboardAssociationDataBase;
