import React, { useState } from "react";
import { Table } from "react-bootstrap";
import { AssociationMembershipType, AssociationsApi } from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import AssociationMembershipTypeEditModal from "./AssociationMembershipTypeEditModal.tsx";
import AssociationMembershipTypePriceModal from "./AssociationMembershipTypePriceModal.tsx";
import { getAssociationMembershipTypeCurrentPrice } from "./getAssociationMembershipTypeCurrentPrice.ts";

interface AssociationMembershipTypeTableProps {
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  membershipTypes: AssociationMembershipType[];
  loadData: () => void;
}

const AssociationMembershipTypeTable: React.FC<
  AssociationMembershipTypeTableProps
> = ({ csrfToken, setToastDatas, membershipTypes, loadData }) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [typeSelectedForEdit, setTypeSelectedForEdit] =
    useState<AssociationMembershipType>();
  const [typeSelectedForPrice, setTypeSelectedForPrice] =
    useState<AssociationMembershipType>();
  const [typeSelectedForDeletion, setTypeSelectedForDeletion] =
    useState<AssociationMembershipType>();
  const [deleteLoading, setDeleteLoading] = useState(false);

  function getNextPrice(type: AssociationMembershipType) {
    const now = new Date();
    return type.prices.find((price) => price.validFrom > now);
  }

  function buildPrice(type: AssociationMembershipType) {
    if (type.prices.length === 0) {
      return formatCurrency(0);
    }

    const result = [];
    const currentPrice = getAssociationMembershipTypeCurrentPrice(
      type,
      new Date(),
    );
    if (currentPrice) {
      result.push(formatCurrency(currentPrice.priceAsFloat));
    }

    const nextPrice = getNextPrice(type);
    if (nextPrice) {
      result.push(
        "Ab dem " +
          formatDateNumeric(nextPrice.validFrom) +
          ": " +
          formatCurrency(nextPrice.priceAsFloat),
      );
    }

    return result.join(", ");
  }

  function onConfirmDelete() {
    if (!typeSelectedForDeletion) {
      alert("No type selected for deletion");
      return;
    }

    setDeleteLoading(true);

    const apiCall = typeSelectedForDeletion.canBeHardDeleted
      ? api.associationsApiAssociationMembershipTypeHardDeleteDestroy.bind(api)
      : api.associationsApiAssociationMembershipTypeSoftDeleteDestroy.bind(api);

    apiCall({
      typeId: typeSelectedForDeletion.id!,
    })
      .then(() => {
        loadData();
        setTypeSelectedForDeletion(undefined);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen der Mitgliedschaft-Typ",
          setToastDatas,
        ),
      )
      .finally(() => setDeleteLoading(false));
  }

  function getDeleteModalText() {
    if (typeSelectedForDeletion === undefined) {
      return <p>error</p>;
    }

    if (typeSelectedForDeletion.canBeHardDeleted) {
      return (
        <p>
          Es existieren keine Mitgliedschaften mit dem Mitgliedschaft-Typ "
          {typeSelectedForDeletion.name}". Der Mitgliedschaft-Typ wir gelöscht.
        </p>
      );
    } else {
      return (
        <div>
          <p>
            Es gibt Mitgliedschaften die mit dem Mitgliedschaft-Typ "
            {typeSelectedForDeletion.name}" verbunden sind (egal ob aktuell
            vergangen), deswegen kann er nicht gelöscht werden.
          </p>
          <p>
            Stattdessen wird es aus der BestellWizard versteckt so dass neue
            Mitglieder diesen Typ nicht mehr auswählen können.
          </p>
          <p>Bestehende Mitgliedschaften dieses Types bleiben unverändert.</p>
        </div>
      );
    }
  }

  return (
    <>
      <Table hover responsive bordered>
        <thead>
          <tr>
            <th>Name</th>
            <th>Preis</th>
            <th>Reihenfolge</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {membershipTypes.map((type) => (
            <tr key={type.id}>
              <td>
                <span
                  className={type.deleted ? "text-decoration-line-through" : ""}
                >
                  {type.name}
                </span>
              </td>
              <td>{buildPrice(type)}</td>
              <td>{type.orderInBestellWizard}</td>
              <td>
                <div className={"d-flex gap-2"}>
                  <TapirButton
                    variant={"outline-primary"}
                    icon={"edit"}
                    size={"sm"}
                    onClick={() => setTypeSelectedForEdit(type)}
                  />
                  <TapirButton
                    variant={"outline-primary"}
                    icon={"euro"}
                    size={"sm"}
                    onClick={() => setTypeSelectedForPrice(type)}
                  />
                  {type.deleted ? (
                    <TapirHelpButton
                      text={
                        "Dieser Mitgliedschaft-Typ ist versteckt. Es kann nicht gelöscht werden weil es mit bestehende Mitgliedschaften verbunden ist. Es wird neue Mitglieder nicht angeboten."
                      }
                      buttonSize={"sm"}
                    />
                  ) : (
                    <TapirButton
                      variant={"outline-danger"}
                      icon={"delete"}
                      size={"sm"}
                      onClick={() => setTypeSelectedForDeletion(type)}
                    />
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      {typeSelectedForEdit && (
        <AssociationMembershipTypeEditModal
          csrfToken={csrfToken}
          show={true}
          onHide={() => setTypeSelectedForEdit(undefined)}
          onEdited={() => {
            loadData();
            setTypeSelectedForEdit(undefined);
          }}
          setToastDatas={setToastDatas}
          membershipType={typeSelectedForEdit}
        />
      )}
      {typeSelectedForPrice && (
        <AssociationMembershipTypePriceModal
          csrfToken={csrfToken}
          show={true}
          onHide={() => setTypeSelectedForPrice(undefined)}
          onEdited={() => {
            loadData();
          }}
          setToastDatas={setToastDatas}
          membershipType={typeSelectedForPrice}
        />
      )}
      {typeSelectedForDeletion && (
        <ConfirmDeleteModal
          message={getDeleteModalText()}
          open={true}
          onConfirm={onConfirmDelete}
          onCancel={() => setTypeSelectedForDeletion(undefined)}
          loading={deleteLoading}
          confirmButtonText={
            typeSelectedForDeletion.canBeHardDeleted ? "Löschen" : "Verstecken"
          }
        />
      )}
    </>
  );
};

export default AssociationMembershipTypeTable;
