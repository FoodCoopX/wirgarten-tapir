import React, { useEffect, useRef, useState } from "react";
import { Form, Modal, Spinner, Table } from "react-bootstrap";
import { LocationRoute, PickupLocationsApi } from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface LocationRouteModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const LocationRouteModal: React.FC<LocationRouteModalProps> = ({
  show,
  onHide,
  csrfToken,
  setToastDatas,
}) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [routes, setRoutes] = useState<LocationRoute[]>([]);
  const [selectedForDeletion, setSelectedForDeletion] =
    useState<LocationRoute>();
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [newRouteName, setNewRouteName] = useState("");
  const [saveLoading, setSaveLoading] = useState(false);
  const [selectedForEdition, setSelectedForEdition] = useState<LocationRoute>();
  const [editedRouteName, setEditedRouteName] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!show) return;

    setSelectedForEdition(undefined);
    setSelectedForDeletion(undefined);

    loadData();
  }, [show]);

  useEffect(() => {
    if (selectedForEdition !== undefined) {
      setEditedRouteName(selectedForEdition.name);
    }
  }, [selectedForEdition]);

  function loadData() {
    setDataLoading(true);

    api
      .pickupLocationsLocationRoutesList()
      .then(setRoutes)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Ausfahrrunden",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }

  function onConfirmDelete() {
    if (selectedForDeletion === undefined) {
      alert("Keine Runde ausgewählt");
      return;
    }

    setDeleteLoading(true);

    api
      .pickupLocationsLocationRoutesDestroy({ id: selectedForDeletion.id! })
      .then(() => {
        setRoutes(
          routes.filter((route) => route.id !== selectedForDeletion.id),
        );
        setSelectedForDeletion(undefined);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen der Ausfahrrunde",
          setToastDatas,
        ),
      )
      .finally(() => setDeleteLoading(false));
  }

  function onCreate() {
    if (!formRef.current) {
      return;
    }

    if (!formRef.current.reportValidity()) {
      return;
    }

    setSaveLoading(true);

    api
      .pickupLocationsLocationRoutesCreate({
        locationRouteRequest: { name: newRouteName },
      })
      .then(loadData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Ausfahrrunde",
          setToastDatas,
        ),
      )
      .finally(() => {
        setSaveLoading(false);
        setNewRouteName("");
      });
  }

  function onEdit() {
    if (editedRouteName.trim() === "") {
      alert("Die Name darf nicht leer sein");
      return;
    }

    if (selectedForEdition === undefined) {
      alert("Keine Runde ausgewählt");
      return;
    }

    setEditLoading(true);

    api
      .pickupLocationsLocationRoutesUpdate({
        id: selectedForEdition.id!,
        locationRouteRequest: { name: editedRouteName },
      })
      .then(loadData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Editieren der Ausfahrrunde",
          setToastDatas,
        ),
      )
      .finally(() => {
        setEditLoading(false);
        setSelectedForEdition(undefined);
      });
  }

  function getDeleteModalText() {
    if (selectedForDeletion === undefined) {
      return "ERROR";
    }

    let result =
      "Bist du sicher das du die Runde " +
      selectedForDeletion.name +
      " löschen willst?";

    if (selectedForDeletion.pickupLocationNames.length > 0) {
      result +=
        " Folgende Abholorte sind gerade auf dieser Runde: " +
        selectedForDeletion.pickupLocationNames.join(", ");
    }

    return result;
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <Modal.Body>
        <Table striped hover responsive>
          <thead>
            <tr>
              <th>Name</th>
              <th>Abholorte</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {routes.map((route) => (
              <tr key={route.id}>
                <td>
                  {selectedForEdition !== route && <span>{route.name}</span>}
                  {selectedForEdition === route && (
                    <Form.Control
                      value={editedRouteName}
                      onChange={(event) =>
                        setEditedRouteName(event.target.value)
                      }
                    />
                  )}
                </td>
                <td>
                  {route.pickupLocationNames.length === 0
                    ? "Keine"
                    : route.pickupLocationNames.join(", ")}
                </td>
                <td>
                  <div className={"d-flex gap-2"}>
                    {selectedForEdition !== route && (
                      <TapirButton
                        variant={"outline-primary"}
                        icon={"edit"}
                        size={"sm"}
                        onClick={() => setSelectedForEdition(route)}
                      />
                    )}
                    {selectedForEdition === route && (
                      <TapirButton
                        variant={"primary"}
                        icon={"save"}
                        size={"sm"}
                        onClick={onEdit}
                        loading={editLoading}
                      />
                    )}
                    <TapirButton
                      variant={"outline-danger"}
                      icon={"delete"}
                      size={"sm"}
                      onClick={() => setSelectedForDeletion(route)}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
        <h6 className={"mt-2"}>Ausfahrrunde hinzufügen</h6>
        <Form className={"d-flex gap-2 align-items-end"} ref={formRef}>
          <Form.Group>
            <Form.Label>Name</Form.Label>
            <Form.Control
              required={true}
              value={newRouteName}
              onChange={(event) => setNewRouteName(event.target.value)}
            />
          </Form.Group>
          <TapirButton
            variant={"primary"}
            icon={"add"}
            onClick={onCreate}
            loading={saveLoading}
            type={"submit"}
          />
        </Form>
      </Modal.Body>
    );
  }

  return (
    <>
      <Modal
        show={show && !selectedForDeletion}
        onHide={onHide}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>Ausfahrrunden verwalten</h5>
        </Modal.Header>
        {getModalBody()}
      </Modal>
      {selectedForDeletion && (
        <ConfirmDeleteModal
          message={getDeleteModalText()}
          open={true}
          onConfirm={onConfirmDelete}
          onCancel={() => setSelectedForDeletion(undefined)}
          loading={deleteLoading}
        />
      )}
    </>
  );
};

export default LocationRouteModal;
