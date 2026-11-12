import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";
import { PublicWaitingListEntryDetails, WaitingListApi } from "../api-client";
import BestellWizardMobile from "../bestell_wizard_mobile/BestellWizardMobile.tsx";
import { useApi } from "../hooks/useApi.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

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
      .catch((error) => {
        if (error?.response?.status === 404) return;
        handleRequestError(error, "Fehler beim Laden der Warteliste-Eintrag!");
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
      Der Link ist bereits abgelaufen. Bitte wende dich an die Verwaltung (
      <a href={"mailto:" + adminEmail}>{adminEmail}</a>).
    </p>
  );
};

export default WaitingListConfirmBase;
