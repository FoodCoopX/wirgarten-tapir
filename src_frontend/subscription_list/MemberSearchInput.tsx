import React, { useEffect, useState } from "react";
import { Form, InputGroup, ListGroup, Spinner } from "react-bootstrap";
import {
  AdminSubscriptionChangeMemberSummary,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

const SEARCH_DELAY_MS = 300;

const HELP_TEXT = (
  <p className={"mb-0"}>
    Suche nach Mitgliedsnummer, Vorname oder Nachname, auch kombiniert (z.B. "12
    Erika" oder "Erika Mustermann").
  </p>
);

interface MemberSearchInputProps {
  memberId: string | undefined;
  memberSummary: AdminSubscriptionChangeMemberSummary | undefined;
  setMemberId: (memberId: string | undefined) => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

function formatMemberSummary(member: AdminSubscriptionChangeMemberSummary) {
  if (member.memberNumber === null) {
    return member.displayName;
  }
  return `${member.memberNumber} · ${member.displayName}`;
}

const MemberSearchInput: React.FC<MemberSearchInputProps> = ({
  memberId,
  memberSummary,
  setMemberId,
  setToastDatas,
}) => {
  const api = useApi(SubscriptionsApi);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<
    AdminSubscriptionChangeMemberSummary[]
  >([]);
  const [searching, setSearching] = useState(false);
  const [preselecting, setPreselecting] = useState(false);

  useEffect(() => {
    const subscriptionId = getParameterFromUrl("contract");
    if (!subscriptionId || memberId !== undefined) {
      return;
    }

    setPreselecting(true);
    api
      .subscriptionsSubscriptionsRetrieve({ id: subscriptionId })
      .then((subscription) => setMemberId(subscription.member))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden des ausgewählten Vertrags",
          setToastDatas,
        ),
      )
      .finally(() => setPreselecting(false));
  }, []);

  useEffect(() => {
    if (search.trim() === "") {
      setResults([]);
      return;
    }

    let cancelled = false;
    const timeout = setTimeout(() => {
      setSearching(true);
      api
        .subscriptionsApiAdminSubscriptionChangeMemberSearchList({ search })
        .then((members) => {
          if (!cancelled) setResults(members);
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler bei der Mitgliedersuche",
            setToastDatas,
          ),
        )
        .finally(() => {
          if (!cancelled) setSearching(false);
        });
    }, SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [search]);

  if (preselecting) {
    return <Spinner size={"sm"} />;
  }

  if (memberId !== undefined) {
    return (
      <div className={"d-flex flex-row gap-2 align-items-center"}>
        <strong>
          {memberSummary ? (
            formatMemberSummary(memberSummary)
          ) : (
            <Spinner size={"sm"} />
          )}
        </strong>
        <TapirButton
          variant={"outline-secondary"}
          size={"sm"}
          icon={"person_search"}
          text={"Anderes Mitglied"}
          onClick={() => {
            setSearch("");
            setMemberId(undefined);
          }}
        />
      </div>
    );
  }

  return (
    <div className={"d-flex flex-column gap-2"}>
      <InputGroup>
        <Form.Control
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={"Mitgliedsnummer, Vorname, Nachname"}
          autoFocus
        />
        <TapirHelpButton text={HELP_TEXT} />
      </InputGroup>
      {searching && <Spinner size={"sm"} />}
      {!searching && search.trim() !== "" && results.length === 0 && (
        <span className={"text-muted"}>Kein Mitglied gefunden.</span>
      )}
      {results.length > 0 && (
        <ListGroup style={{ maxHeight: "300px", overflowY: "auto" }}>
          {results.map((member) => (
            <ListGroup.Item
              key={member.id}
              action
              onClick={() => setMemberId(member.id)}
            >
              {formatMemberSummary(member)}
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </div>
  );
};

export default MemberSearchInput;
