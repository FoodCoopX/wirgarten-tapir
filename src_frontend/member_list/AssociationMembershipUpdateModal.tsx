import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Col, Form, Modal, Row, Spinner } from "react-bootstrap";
import {
  AssociationMembership,
  AssociationMembershipType,
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
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AssociationMembershipUpdateModalProps {
  memberId: string;
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  reloadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const AssociationMembershipUpdateModal: React.FC<
  AssociationMembershipUpdateModalProps
> = ({ memberId, csrfToken, show, onHide, reloadData, setToastDatas }) => {
  const associationApi = useApi(AssociationsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [membershipTypes, setMembershipTypes] = useState<
    AssociationMembershipType[]
  >([]);
  const [selectedMembershipTypeId, setSelectedMembershipTypeId] = useState("");
  const [startDateAsString, setStartDateAsString] = useState("");
  const [memberships, setMemberships] = useState<AssociationMembership[]>([]);
  const [member, setMember] = useState<Member>();

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);

    associationApi
      .associationsAssociationMembershipTypesList()
      .then((types) => {
        setMembershipTypes(types);
        if (types.length > 0) {
          setSelectedMembershipTypeId(types[0].id!);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitdlieschafttypen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  useEffect(() => {
    if (!show) {
      return;
    }

    setMemberships([]);

    associationApi
      .associationsApiMemberAssociationMembershipsRetrieve({
        memberId: memberId,
      })
      .then((response) => {
        setMemberships(response.memberships);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitglieschaften",
          setToastDatas,
        ),
      );

    coopApi
      .coopMembersRetrieve({ id: memberId })
      .then(setMember)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitgliedsdaten",
          setToastDatas,
        ),
      );
  }, [show, memberId]);

  function onCreate() {
    if (selectedMembershipTypeId === "") {
      alert("Kein ausgewählter Mitgliedschafttyp");
      return;
    }

    const startDate = new Date(startDateAsString);
    if (Number.isNaN(startDate.valueOf())) {
      alert("Ungültiges Datum");
      return;
    }

    setSaving(true);
    associationApi
      .associationsApiAdminCreateMembershipCreate({
        adminSetAssociationMembershipRequestRequest: {
          membershipTypeId: selectedMembershipTypeId,
          memberId: memberId,
          startDate: startDate,
        },
      })
      .then(() => {
        onHide();
        reloadData();
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
          <Modal.Title>Vereinsmitgliedschaft als Admin erzeugen</Modal.Title>
          <TapirHelpButton
            text={
              <>
                <p>
                  Bestehen Mitgliedschaften die nach dem ausgewähltem
                  Start-Datum beginnen werden gelöscht.
                </p>
                <p>
                  Bestehen Mitgliedschaften die aktiv am ausgewähltem
                  Start-Datum sind werden geendet mit End-Datum am Tag vor dem
                  Start-Datum.s
                </p>
              </>
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
            <Row className={"mt-2"}>
              <Col>
                {membershipTypes.length === 0 ? (
                  "Keine Mitgliedschafttypen"
                ) : (
                  <>
                    <h6>Neue Mitgliedschaft</h6>
                    <div className={"d-flex flex-column gap-2"}>
                      <Form.Group>
                        <Form.Label>Mitgliedschafttyp</Form.Label>
                        <Form.Select
                          onChange={(event) =>
                            setSelectedMembershipTypeId(event.target.value)
                          }
                        >
                          {membershipTypes.map((type) => {
                            return (
                              <option key={type.id} value={type.id}>
                                {type.name}
                              </option>
                            );
                          })}
                        </Form.Select>
                      </Form.Group>
                      <Form.Group>
                        <Form.Label>Start-Datum</Form.Label>
                        <Form.Control
                          type={"date"}
                          value={startDateAsString}
                          onChange={(event) =>
                            setStartDateAsString(event.target.value)
                          }
                        />
                      </Form.Group>
                    </div>
                  </>
                )}
              </Col>
            </Row>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          text={"Erzeugen"}
          icon={"save"}
          onClick={onCreate}
          loading={saving}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default AssociationMembershipUpdateModal;
