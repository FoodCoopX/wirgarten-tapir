import React, { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi.ts";
import { PublicWaitingListEntryDetails, WaitingListApi } from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { Spinner } from "react-bootstrap";
import BestellWizardMobile from "../bestell_wizard_mobile/BestellWizardMobile.tsx";

interface WaitingListConfirmBaseProps {
  csrfToken: string;
  waitingListEntryId: string;
  waitingListLinkKey: string;
  adminEmail: string;
}

const WaitingListConfirmBase: React.FC<WaitingListConfirmBaseProps> = ({
  csrfToken,
  waitingListEntryId,
  waitingListLinkKey,
  adminEmail,
}) => {
  const api = useApi(WaitingListApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [waitingListEntryDetails, setWaitingListEntryDetails] =
    useState<PublicWaitingListEntryDetails>();

  useEffect(() => {
    api
      .waitingListApiPublicGetWaitingListEntryDetailsRetrieve({
        entryId: waitingListEntryId,
        linkKey: waitingListLinkKey,
      })
      .then(setWaitingListEntryDetails)
      .catch(async (error) => {
        if (error?.response?.status === 404) return;
        await handleRequestError(
          error,
          "Fehler beim Laden der Warteliste-Eintrag!",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <Spinner />;
  }

  if (waitingListEntryDetails) {
    return (
      <BestellWizardMobile
        csrfToken={csrfToken}
        waitingListEntryDetails={waitingListEntryDetails}
      />
    );
  }

  return (
    <p>
      Der Link ist bereits abgelaufen. Bitte wende dich an{" "}
      <a href={"mailto:" + adminEmail}>{adminEmail}</a>
    </p>
  );
};

export default WaitingListConfirmBase;
