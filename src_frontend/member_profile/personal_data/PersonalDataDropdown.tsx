import "dayjs/locale/de";
import React, { useState } from "react";
import { Dropdown } from "react-bootstrap";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import MemberEmailModal from "./MemberEmailModal.tsx";
import MemberExtraEmailsModal from "./MemberExtraEmailsModal.tsx";
import MemberPersonalDataModal from "./MemberPersonalDataModal.tsx";

interface PersonalDataDropdownProps {
  memberId: string;
  csrfToken: string;
  extraEmailAddressesEnabled: boolean;
}

const PersonalDataDropdown: React.FC<PersonalDataDropdownProps> = ({
  memberId,
  csrfToken,
  extraEmailAddressesEnabled,
}) => {
  const [showPersonalDataModal, setShowPersonalDataModal] = useState(false);
  const [showMailEmailModal, setShowMailEmailModal] = useState(false);
  const [showExtraEmailsModal, setShowExtraEmailsModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <Dropdown>
        <Dropdown.Toggle variant={"outline-primary"}>
          <span className={"material-icons"}>edit</span>
        </Dropdown.Toggle>
        <Dropdown.Menu>
          <Dropdown.Item onClick={() => setShowPersonalDataModal(true)}>
            Persönliche Daten
          </Dropdown.Item>
          <Dropdown.Item onClick={() => setShowMailEmailModal(true)}>
            {extraEmailAddressesEnabled && "Haupt-"}E-Mail-Adresse
          </Dropdown.Item>
          {extraEmailAddressesEnabled && (
            <Dropdown.Item onClick={() => setShowExtraEmailsModal(true)}>
              Zusätzliche E-Mail-Adressen
            </Dropdown.Item>
          )}
        </Dropdown.Menu>
      </Dropdown>
      <MemberPersonalDataModal
        memberId={memberId}
        csrfToken={csrfToken}
        setToastDatas={setToastDatas}
        show={showPersonalDataModal}
        onHide={() => setShowPersonalDataModal(false)}
      />
      <MemberEmailModal
        memberId={memberId}
        csrfToken={csrfToken}
        setToastDatas={setToastDatas}
        show={showMailEmailModal}
        onHide={() => setShowMailEmailModal(false)}
      />
      <MemberExtraEmailsModal
        memberId={memberId}
        csrfToken={csrfToken}
        setToastDatas={setToastDatas}
        show={showExtraEmailsModal}
        onHide={() => setShowExtraEmailsModal(false)}
      />
      <div className={"d-flex gap-2"}>
        <TapirToastContainer
          toastDatas={toastDatas}
          setToastDatas={setToastDatas}
        />
      </div>
    </>
  );
};

export default PersonalDataDropdown;
