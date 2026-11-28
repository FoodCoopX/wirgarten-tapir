import React, { useState } from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import AdminDashboardNumberOfAssociationCancellations from "./AdminDashboardNumberOfAssociationCancellations.tsx";
import AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate from "./AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate.tsx";
import AdminDashboardNumberOfAssociationMembers from "./AdminDashboardNumberOfAssociationMembers.tsx";

const AdminDashboardAssociationDataBase: React.FC = () => {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <div className={"d-flex gap-2"}>
        <TapirButton
          icon={"bar_chart"}
          variant={"outline-secondary"}
          text={"Graphen zu Vereinsmitgliedschaften anzeigen"}
          onClick={() => setShowModal(true)}
        />
      </div>
      {showModal && (
        <Modal show={showModal} onHide={() => setShowModal(false)} size={"xl"}>
          <Modal.Body>
            <div className={"d-flex gap-2 flex-column"}>
              <AdminDashboardNumberOfAssociationMembers />
              <AdminDashboardNumberOfAssociationCancellations />
              <AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate />
            </div>
          </Modal.Body>
        </Modal>
      )}
    </>
  );
};

export default AdminDashboardAssociationDataBase;
