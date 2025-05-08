import React from "react";
import { PickupLocation, WaitingListPickupLocationWish } from "../api-client";
import "./waiting_list_card.css";
import { ButtonGroup, Form, Row, Table } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";

interface PickupLocationWishesEditorProps {
  pickupLocations: PickupLocation[];
  wishes: WaitingListPickupLocationWish[];
  setWishes: (wishes: WaitingListPickupLocationWish[]) => void;
  waitingListEntryId: string;
}

const PickupLocationWishesEditor: React.FC<PickupLocationWishesEditorProps> = ({
  pickupLocations,
  wishes,
  setWishes,
  waitingListEntryId,
}) => {
  function removeWish(wishToRemove: WaitingListPickupLocationWish) {
    setWishes(wishes.filter((wish) => wish.id !== wishToRemove.id));
  }

  function moveWishUp(index: number) {
    swapWishIndex(index, index - 1);
  }

  function moveWishDown(index: number) {
    swapWishIndex(index, index + 1);
  }

  function swapWishIndex(indexA: number, indexB: number) {
    const wishA = wishes[indexA];
    const wishB = wishes[indexB];
    wishes[indexB] = wishA;
    wishes[indexA] = wishB;
    wishA.priority = indexB + 1;
    wishB.priority = indexA + 1;

    setWishes([...wishes]);
  }

  function addWish(pickupLocationId: string) {
    const pickupLocation = pickupLocations.find(
      (pickupLocation) => pickupLocation.id === pickupLocationId,
    );
    if (!pickupLocation) {
      alert("Pickup location not found. ID: " + pickupLocationId);
      return;
    }
    wishes.push({
      id: undefined,
      pickupLocation: pickupLocation,
      priority: wishes.length + 1,
      waitingListEntry: waitingListEntryId,
    });
    setWishes([...wishes]);
  }

  return (
    <>
      <Row>
        <h5>Abholort-Wechselwünsche</h5>
      </Row>
      <Row>
        {wishes.length === 0 ? (
          <span className={"mb-2"}>Kein Wechselwunsch</span>
        ) : (
          <Table striped hover responsive>
            <thead>
              <tr>
                <th>Priorität</th>
                <th>Abholort</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {wishes.map((wish, index) => {
                return (
                  <tr key={wish.id}>
                    <td>{wish.priority}</td>
                    <td>{wish.pickupLocation.name}</td>
                    <td>
                      <ButtonGroup size={"sm"}>
                        <TapirButton
                          variant={"outline-secondary"}
                          icon={"arrow_drop_up"}
                          onClick={() => moveWishUp(index)}
                          size={"sm"}
                          disabled={index === 0}
                        />
                        <TapirButton
                          variant={"outline-secondary"}
                          icon={"arrow_drop_down"}
                          onClick={() => moveWishDown(index)}
                          size={"sm"}
                          disabled={index === wishes.length - 1}
                        />
                        <TapirButton
                          variant={"outline-danger"}
                          icon={"delete"}
                          onClick={() => removeWish(wish)}
                          size={"sm"}
                        />
                      </ButtonGroup>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Row>
      <Row>
        <Form.Select onChange={(event) => addWish(event.target.value)}>
          <option value={-1}>Abholort-Wunsch hinzufügen</option>
          {pickupLocations
            .filter(
              (pickupLocation) =>
                !wishes
                  .map((wish) => wish.pickupLocation.id)
                  .includes(pickupLocation.id),
            )
            .map((pickupLocation) => (
              <option key={pickupLocation.id} value={pickupLocation.id}>
                {pickupLocation.name}
              </option>
            ))}
        </Form.Select>
      </Row>
    </>
  );
};

export default PickupLocationWishesEditor;
