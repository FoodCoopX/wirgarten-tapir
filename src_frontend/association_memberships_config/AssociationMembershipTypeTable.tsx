import React, { useState } from "react";
import { Table } from "react-bootstrap";
import { AssociationMembershipType } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import AssociationMembershipTypeEditModal from "./AssociationMembershipTypeEditModal.tsx";
import AssociationMembershipTypePriceModal from "./AssociationMembershipTypePriceModal.tsx";

interface AssociationMembershipTypeTableProps {
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  membershipTypes: AssociationMembershipType[];
  loadData: () => void;
}

const AssociationMembershipTypeTable: React.FC<
  AssociationMembershipTypeTableProps
> = ({ csrfToken, setToastDatas, membershipTypes, loadData }) => {
  const [typeSelectedForEdit, setTypeSelectedForEdit] =
    useState<AssociationMembershipType>();
  const [typeSelectedForPrice, setTypeSelectedForPrice] =
    useState<AssociationMembershipType>();

  function getCurrentPrice(type: AssociationMembershipType) {
    const now = new Date();
    return type.prices.findLast((price) => price.validFrom < now);
  }

  function getNextPrice(type: AssociationMembershipType) {
    const now = new Date();
    return type.prices.find((price) => price.validFrom > now);
  }

  function buildPrice(type: AssociationMembershipType) {
    if (type.prices.length === 0) {
      return formatCurrency(0);
    }

    const result = [];
    const currentPrice = getCurrentPrice(type);
    if (currentPrice) {
      result.push(formatCurrency(Number.parseFloat(currentPrice.price)));
    }

    const nextPrice = getNextPrice(type);
    if (nextPrice) {
      result.push(
        "Ab dem " +
          formatDateNumeric(nextPrice.validFrom) +
          ": " +
          formatCurrency(Number.parseFloat(nextPrice.price)),
      );
    }

    return result.join(", ");
  }

  return (
    <>
      <Table hover responsive bordered>
        <thead>
          <tr>
            <th>Name</th>
            <th>Preis</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {membershipTypes.map((type) => (
            <tr key={type.id}>
              <td>{type.name}</td>
              <td>{buildPrice(type)}</td>
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
                  <TapirButton
                    variant={"outline-danger"}
                    icon={"delete"}
                    size={"sm"}
                    onClick={() => alert("WIP")}
                  />
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
    </>
  );
};

export default AssociationMembershipTypeTable;
