import React, { useId, useState } from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import AdminDashboardNumberOfAssociationCancellations from "./AdminDashboardNumberOfAssociationCancellations.tsx";
import AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate from "./AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate.tsx";
import AdminDashboardNumberOfAssociationMembers from "./AdminDashboardNumberOfAssociationMembers.tsx";

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
              <AdminDashboardNumberOfAssociationMembers csrfToken={csrfToken} />
              <AdminDashboardNumberOfAssociationCancellations
                csrfToken={csrfToken}
              />
              <AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate
                csrfToken={csrfToken}
              />
            </div>
          </Modal.Body>
        </Modal>
      )}
    </>
  );
};

export default AdminDashboardAssociationDataBase;
