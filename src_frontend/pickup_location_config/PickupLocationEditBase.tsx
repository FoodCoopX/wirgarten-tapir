import React, { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { PickupLocationsApi, ResponseError } from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "../utils/addToast.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { URL_PARAMETER_PICKUP_LOCATION_ID } from "./constants.ts";
import PickupLocationEditModal from "./PickupLocationEditModal.tsx";

interface PickupLocationEditBaseProps {
  csrfToken: string;
}

function reloadWithSelectedLocation(pickupLocationId: string | null) {
  const url = new URL(window.location.href);
  if (pickupLocationId === null) {
    url.searchParams.delete(URL_PARAMETER_PICKUP_LOCATION_ID);
  } else {
    url.searchParams.set(URL_PARAMETER_PICKUP_LOCATION_ID, pickupLocationId);
  }
  window.location.assign(url.toString());
}

const PickupLocationEditBase: React.FC<PickupLocationEditBaseProps> = ({
  csrfToken,
}) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [showEditModal, setShowEditModal] = useState(false);
  const [editedLocationId, setEditedLocationId] = useState<string | null>(null);
  const [locationIdToDelete, setLocationIdToDelete] = useState<string | null>(
    null,
  );
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function getSelectedLocationId(): string | null {
    const pickupLocationId = getParameterFromUrl(
      URL_PARAMETER_PICKUP_LOCATION_ID,
    );
    if (!pickupLocationId) {
      alert("Du musst erst einen Abholort auswählen.");
      return null;
    }
    return pickupLocationId;
  }

  function onAddClick() {
    setEditedLocationId(null);
    setShowEditModal(true);
  }

  function onEditClick() {
    const pickupLocationId = getSelectedLocationId();
    if (!pickupLocationId) return;
    setEditedLocationId(pickupLocationId);
    setShowEditModal(true);
  }

  function onDeleteClick() {
    setLocationIdToDelete(getSelectedLocationId());
  }

  function onConfirmDelete() {
    if (locationIdToDelete === null) return;

    setDeleteLoading(true);

    api
      .pickupLocationsPickupLocationsDestroy({ id: locationIdToDelete })
      .then(() => reloadWithSelectedLocation(null))
      .catch(async (error) => {
        setLocationIdToDelete(null);
        if (error instanceof ResponseError && error.response.status === 400) {
          addToast(
            {
              title: "Der Abholort kann nicht gelöscht werden",
              message: await error.response.json(),
              variant: "danger",
              id: uuidv4(),
            },
            setToastDatas,
          );
          return;
        }
        handleRequestError(
          error,
          "Fehler beim Löschen des Abholorts",
          setToastDatas,
        );
      })
      .finally(() => setDeleteLoading(false));
  }

  return (
    <div className={"d-flex gap-2"}>
      <TapirButton
        icon={"add_location_alt"}
        variant={"outline-success"}
        onClick={onAddClick}
        tooltip={"Abholort hinzufügen"}
      />
      <TapirButton
        icon={"edit"}
        variant={"outline-primary"}
        onClick={onEditClick}
        tooltip={"Abholort bearbeiten"}
      />
      <TapirButton
        icon={"delete"}
        variant={"outline-danger"}
        onClick={onDeleteClick}
        tooltip={"Abholort löschen"}
      />
      <PickupLocationEditModal
        show={showEditModal}
        onHide={() => setShowEditModal(false)}
        csrfToken={csrfToken}
        setToastDatas={setToastDatas}
        pickupLocationId={editedLocationId}
        onSaved={(pickupLocation) =>
          reloadWithSelectedLocation(pickupLocation.id!)
        }
      />
      <ConfirmDeleteModal
        message={"Möchtest du diesen Abholort wirklich löschen?"}
        open={locationIdToDelete !== null}
        onConfirm={onConfirmDelete}
        onCancel={() => setLocationIdToDelete(null)}
        loading={deleteLoading}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};

export default PickupLocationEditBase;
