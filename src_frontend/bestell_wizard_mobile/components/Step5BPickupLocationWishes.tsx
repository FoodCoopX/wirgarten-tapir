import React from "react";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import "./map.css";
import "leaflet/dist/leaflet.css";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { Form } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

interface Step5BPickupLocationWishesProps {
  selectedPickupLocations: PublicPickupLocation[];
  setSelectedPickupLocations: (locations: PublicPickupLocation[]) => void;
  pickupLocationsWithCapacityFull: Set<PublicPickupLocation>;
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  productTypesInWaitingList: Set<PublicProductType>;
}

const Step5BPickupLocationWishes: React.FC<Step5BPickupLocationWishesProps> = ({
  selectedPickupLocations,
  setSelectedPickupLocations,
  pickupLocationsWithCapacityFull,
  settings,
  shoppingCart,
  productTypesInWaitingList,
}) => {
  function setPickupLocationAtIndex(
    pickupLocation: PublicPickupLocation,
    index: number,
  ) {
    selectedPickupLocations[index] = pickupLocation;

    setSelectedPickupLocations([...new Set(selectedPickupLocations)]);
  }

  function getOptions(index: number) {
    let options = settings.pickupLocations;
    for (let i = 0; i < index; i++) {
      options = options.filter(
        (pickupLocation) => pickupLocation !== selectedPickupLocations[i],
      );
    }

    return options;
  }

  function getWishLabel(index: number) {
    let label = index + 1 + ". Wunsch";
    if (!pickupLocationsWithCapacityFull.has(selectedPickupLocations[index])) {
      label += " (Beim Einstieg)";
    } else {
      label += " (Warteliste-Eintrag)";
    }

    return label;
  }

  return (
    <div className={"d-flex flex-column gap-2 align-items-center"}>
      {selectedPickupLocations.map((selectedPickupLocation, index) => (
        <Form.Group key={index}>
          <Form.Label>{getWishLabel(index)}</Form.Label>
          <div className="d-flex flex-row gap-2">
            <Form.Select
              style={{ maxWidth: "200px" }}
              onChange={(event) =>
                setPickupLocationAtIndex(
                  settings.pickupLocations.find(
                    (pickupLocation) =>
                      pickupLocation.id === event.target.value,
                  )!,
                  index,
                )
              }
              value={selectedPickupLocation.id}
            >
              {getOptions(index).map((pickupLocation) => (
                <option key={pickupLocation.id} value={pickupLocation.id}>
                  {pickupLocation.name}
                </option>
              ))}
            </Form.Select>
            <TapirButton
              variant={"outline-danger"}
              size={"sm"}
              icon={"delete"}
              onClick={() =>
                setSelectedPickupLocations(
                  selectedPickupLocations.filter(
                    (_, index2) => index2 !== index,
                  ),
                )
              }
            />
          </div>
        </Form.Group>
      ))}
      {selectedPickupLocations.length < 3 && (
        <TapirButton
          variant={BUTTON_VARIANT}
          text={"Weiterer Wunsch"}
          icon={"add_circle"}
          onClick={() =>
            setSelectedPickupLocations([
              ...selectedPickupLocations,
              settings.pickupLocations[0],
            ])
          }
        />
      )}
    </div>
  );
};

export default Step5BPickupLocationWishes;
