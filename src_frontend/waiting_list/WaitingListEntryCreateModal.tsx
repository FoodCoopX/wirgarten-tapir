import React, { useEffect, useState } from "react";
import { Modal } from "react-bootstrap";
import Select from "react-select";
import { CoopApi, Member, WaitingListApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import "./waiting_list_card.css";

interface WaitingListEntryCreateModalProps {
  csrfToken: string;
  show: boolean;
  onClose: () => void;
  reloadEntries: () => void;

  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  entryReloading: boolean;
}

const WaitingListEntryCreateModal: React.FC<
  WaitingListEntryCreateModalProps
> = ({
  csrfToken,
  show,
  onClose,
  reloadEntries,
  setToastDatas,
  entryReloading,
}) => {
  const waitingListApi = useApi(WaitingListApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [selectedMember, setSelectedMember] = useState<Member>();
  const [allMembers, setAllMembers] = useState<Member[]>([]);

  useEffect(() => {
    coopApi
      .coopMembersList()
      .then(setAllMembers)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitgliederliste",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    setFirstName(selectedMember?.firstName ?? "");
    setLastName(selectedMember?.lastName ?? "");
    setEmail(selectedMember?.email ?? "");
    setPhoneNumber(selectedMember?.phoneNumber ?? "");
  }, [selectedMember]);

  function onSave() {
    setLoading(true);

    waitingListApi
      .waitingListWaitingListEntriesCreate({
        waitingListEntryRequest: {
          firstName: firstName,
          lastName: lastName,
          email: email,
          member: selectedMember?.id,
          phoneNumber: phoneNumber,
          privacyConsent: new Date(),
          numberOfCoopShares: 0,
        },
      })
      .then(() => {
        reloadEntries();
        onClose();
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Speichern", setToastDatas),
      )
      .finally(() => setLoading(false));
  }

  function buildMemberOptions() {
    return allMembers.map((member) => {
      return {
        value: member.id,
        label:
          member.firstName + " " + member.lastName + " #" + member.memberNo,
      };
    });
  }

  return (
    <Modal show={show} onHide={onClose} centered={true} size={"sm"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Warteliste-Eintrag erzeugen</h5>
      </Modal.Header>
      <Modal.Body>
        <Select
          isSearchable={true}
          options={buildMemberOptions()}
          onChange={(newValue) => {
            setSelectedMember(
              allMembers.find((member) => member.id === newValue?.value),
            );
          }}
        />
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Warteliste-Eintrag erzeugen"}
          onClick={onSave}
          loading={loading || entryReloading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default WaitingListEntryCreateModal;
