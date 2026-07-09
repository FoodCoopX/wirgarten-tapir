import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import {
  AssociationMembership,
  AssociationsApi,
  CoopApi,
  Member,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { getCurrentMembership } from "../member_profile/association_membership/getCurrentMembership.tsx";
import { getFutureMemberships } from "../member_profile/association_membership/getFutureMemberships.tsx";
import { getPastMemberships } from "../member_profile/association_membership/getPastMemberships.tsx";
import { ToastData } from "../types/ToastData.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AssociationMembershipCancelModalProps {
  memberId: string;
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  reloadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const AssociationMembershipCancelModal: React.FC<
  AssociationMembershipCancelModalProps
> = ({ memberId, csrfToken, show, onHide, reloadData, setToastDatas }) => {
  const associationApi = useApi(AssociationsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [endDateAsString, setEndDateAsString] = useState("");
  const [memberships, setMemberships] = useState<AssociationMembership[]>([]);
  const [selectedMembership, setSelectedMembership] =
    useState<AssociationMembership>();
  const [member, setMember] = useState<Member>();

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);

    Promise.all([
      associationApi.associationsApiMemberAssociationMembershipsRetrieve({
        memberId: memberId,
      }),
      coopApi.coopMembersRetrieve({ id: memberId }),
    ])
      .then(([membershipData, member]) => {
        setMemberships(membershipData.memberships);
        if (membershipData.memberships.length > 0) {
          setSelectedMembership(membershipData.memberships[0]);
        }

        setMember(member);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Daten", setToastDatas),
      )
      .finally(() => setLoading(false));
  }, [show]);

  useEffect(() => {
    if (!selectedMembership) return;

    if (selectedMembership.endDate) {
      setEndDateAsString(selectedMembership.endDate.toISOString().slice(0, 10));
    } else {
      setEndDateAsString("");
    }
  }, [selectedMembership]);

  function onSave() {
    if (selectedMembership === undefined) {
      alert("Keine ausgewählte Mitgliedschaft");
      return;
    }

    const endDate = new Date(endDateAsString);
    if (Number.isNaN(endDate.valueOf())) {
      alert("Ungültiges Datum");
      return;
    }

    setSaving(true);
    associationApi
      .associationsApiSetMembershipEndDateCreate({
        setAssociationMembershipEndDateRequestRequest: {
          endDate: endDate,
          membershipId: selectedMembership.id!,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          location.reload();
        } else {
          alert(response.error);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Mitgliedschaft",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal
      className={"mb-2"}
      show={show}
      onHide={onHide}
      centered={true}
      size={"lg"}
    >
      <Modal.Header closeButton={true}>
        <div
          className={"d-flex justify-content-between align-items-center"}
          style={{ width: "100%" }}
        >
          <Modal.Title>Vereinsmitgliedschaft-End-Datum setzen</Modal.Title>
          <TapirHelpButton
            text={
              <p>
                Es wird nur das End-Datum für die ausgewählte Mitgliedschaft
                gesetzt. Es wird nicht geprüft, ob Überschneidungen mit ggf.
                anderen existierenden Mitgliedschaften für dieses Mitglied
                entstehen. Die Produktverträge des Mitgliedes werden nicht
                geändert oder beendet.
              </p>
            }
          />
        </div>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <>
            <Row>
              <Col>
                <h6>
                  Aktuelle Daten für {member?.firstName} {member?.lastName}
                </h6>
                {memberships.length === 0 ? (
                  "Keine Mitgliedschaft"
                ) : (
                  <>
                    {getCurrentMembership(memberships)}
                    {getFutureMemberships(memberships)}
                    {getPastMemberships(memberships)}
                  </>
                )}
              </Col>
            </Row>
            {memberships.length > 0 && (
              <Row className={"mt-2"}>
                <Col>
                  <>
                    <h6>Neues End-Datum der Mitgliedschaft setzen</h6>
                    <div className={"d-flex flex-column gap-2"}>
                      <Form.Group>
                        <Form.Label>Mitgliedschaften</Form.Label>
                        <Form.Select
                          onChange={(event) =>
                            setSelectedMembership(
                              memberships.find(
                                (membership) =>
                                  membership.id == event.target.value,
                              ),
                            )
                          }
                        >
                          {memberships.map((membership) => {
                            return (
                              <option key={membership.id} value={membership.id}>
                                {membership.type.name}
                                {" ab "}
                                {formatDateNumeric(membership.startDate)}
                                {" bis "}
                                {membership.endDate
                                  ? formatDateNumeric(membership.endDate)
                                  : "kein End-Datum"}
                              </option>
                            );
                          })}
                        </Form.Select>
                      </Form.Group>
                      <Form.Group>
                        <Form.Label>End-Datum</Form.Label>
                        <Form.Control
                          type={"date"}
                          value={endDateAsString}
                          onChange={(event) =>
                            setEndDateAsString(event.target.value)
                          }
                        />
                      </Form.Group>
                    </div>
                  </>
                </Col>
              </Row>
            )}
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          text={"Erzeugen"}
          icon={"save"}
          onClick={onSave}
          loading={saving}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default AssociationMembershipCancelModal;
