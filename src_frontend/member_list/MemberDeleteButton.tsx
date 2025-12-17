import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import { useApi } from "../hooks/useApi.ts";
import { CoopApi, Member } from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface MemberDeleteButtonProps {
  csrfToken: string;
}

const MemberDeleteButton: React.FC<MemberDeleteButtonProps> = ({
  csrfToken,
}) => {
  const coopApi = useApi(CoopApi, csrfToken);
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();
  const [loading, setLoading] = useState(false);
  const [member, setMember] = useState<Member>();

  useEffect(() => {
    if (memberId === undefined) return;

    setLoading(true);

    coopApi
      .coopMembersRetrieve({ id: memberId })
      .then(setMember)
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Mitgliedsdaten"),
      )
      .finally(() => setLoading(false));
  }, [memberId]);

  function buildMemberName() {
    if (member === undefined) return "Keine Member-Daten";
    let name = member.firstName + " " + member.lastName;
    if (member.memberNo) {
      name += " #" + member.memberNo;
    }
    return name;
  }

  function onConfirm() {
    setLoading(true);

    coopApi
      .coopApiDeleteMemberDestroy({ memberId: memberId })
      .then(() => {
        location.reload();
        setShowModal(false);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Löschen des Mitglieds"),
      )
      .finally(() => setLoading(false));
  }

  return (
    <>
      <TapirButton
        icon={"person_remove"}
        variant={"outline-danger"}
        onClick={() => {
          const memberId = getParameterFromUrl("member");
          if (!memberId) {
            alert("Du musst erst das Mitglied auswählen.");
            return;
          }
          setMemberId(memberId);
          setShowModal(true);
        }}
      />
      {memberId && (
        <ConfirmDeleteModal
          open={showModal}
          message={
            loading
              ? "Laden..."
              : "Willst du wirklich dieses Mitglied (" +
                buildMemberName() +
                ") löschen? Die verbundene Verträge, Zahlungen und Historie werden damit auch gelöscht. Das sollst du nur machen um Fehler zu korrigieren."
          }
          onConfirm={onConfirm}
          onCancel={() => setShowModal(false)}
          loading={loading}
        />
      )}
    </>
  );
};

export default MemberDeleteButton;
