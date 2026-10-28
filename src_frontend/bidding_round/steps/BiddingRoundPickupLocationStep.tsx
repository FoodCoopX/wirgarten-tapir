import L from "leaflet";
import "leaflet/dist/leaflet.css";
import React, { useState } from "react";
import {
  ButtonGroup,
  Form,
  ListGroup,
  ListGroupItem,
  ToggleButton,
} from "react-bootstrap";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { formatOpeningTimes } from "../../bestell_wizard/utils/formatOpeningTimes.ts";
import "../../bestell_wizard_mobile/components/map.css";
import NextStepButton from "../../bestell_wizard_mobile/components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../../bestell_wizard_mobile/utils/BUTTON_VARIANT.ts";
import TapirButton from "../../components/TapirButton.tsx";
import formatAddress from "../../utils/formatAddress.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { interpolate } from "../../utils/interpolate.ts";
import {
  BiddingRoundPickupLocation,
  BiddingRoundTexts,
} from "../types/BiddingRoundTypes.ts";
import { parseEuroAmount } from "../utils/bidLevels.ts";

type PickupLocationTab = "map" | "list";

interface BiddingRoundPickupLocationStepProps {
  pickupLocations: BiddingRoundPickupLocation[];
  pickupLocationId: string;
  currentPickupLocationId: string;
  setPickupLocationId: (value: string) => void;
  checkCapacity: (
    pickupLocationIdOverride?: string,
  ) => Promise<{ sufficient: boolean; message: string }>;
  onCapacityCheckError: (error: unknown) => void;
  texts: BiddingRoundTexts;
  goToNextStep: () => void;
  stepActive: boolean;
}

function getTabName(tab: PickupLocationTab) {
  switch (tab) {
    case "map":
      return "Karte";
    case "list":
      return "Liste";
  }
}

function getYearlyCharge(pickupLocation: BiddingRoundPickupLocation): number {
  return parseEuroAmount(pickupLocation.yearlyDeliveryCharge) ?? 0;
}

const BiddingRoundPickupLocationStep: React.FC<
  BiddingRoundPickupLocationStepProps
> = ({
  pickupLocations,
  pickupLocationId,
  currentPickupLocationId,
  setPickupLocationId,
  checkCapacity,
  onCapacityCheckError,
  texts,
  goToNextStep,
  stepActive,
}) => {
  const [currentTab, setCurrentTab] = useState<PickupLocationTab>("map");
  const [showValidation, setShowValidation] = useState(false);
  const [capacityError, setCapacityError] = useState("");

  async function selectLocation(id: string) {
    setPickupLocationId(id);
    setCapacityError("");
    try {
      const result = await checkCapacity(id);
      if (!result.sufficient) {
        setCapacityError(
          result.message || "An diesem Abholort ist keine Kapazität mehr frei.",
        );
      }
    } catch (error) {
      onCapacityCheckError(error);
    }
  }

  async function validate() {
    if (!pickupLocationId) {
      setShowValidation(true);
      return;
    }
    try {
      const result = await checkCapacity(pickupLocationId);
      if (!result.sufficient) {
        setCapacityError(
          result.message || "An diesem Abholort ist keine Kapazität mehr frei.",
        );
        return;
      }
    } catch (error) {
      onCapacityCheckError(error);
      return;
    }
    goToNextStep();
  }

  function getMarkerIcon(pickupLocation: BiddingRoundPickupLocation) {
    if (pickupLocation.id === pickupLocationId) {
      return "marker-icon-green.png";
    }
    if (pickupLocation.utilization?.isFull) {
      return "marker-icon-red.png";
    }
    return "marker-icon.png";
  }

  function buildChargeLabel(pickupLocation: BiddingRoundPickupLocation) {
    const yearlyCharge = getYearlyCharge(pickupLocation);
    if (!yearlyCharge) {
      return null;
    }
    return (
      <small className={"text-muted"}>
        {interpolate("+ {charge} / Jahr Lieferzuschlag", {
          charge: formatCurrency(yearlyCharge),
        })}
      </small>
    );
  }

  function buildFullIndicator(pickupLocation: BiddingRoundPickupLocation) {
    if (!isFull(pickupLocation)) {
      return null;
    }
    return (
      <small className={"text-danger"}>
        {isOwnFullLocation(pickupLocation)
          ? "Ausgelastet (dein aktueller Ort)"
          : "Ausgelastet"}
      </small>
    );
  }

  function isFull(pickupLocation: BiddingRoundPickupLocation): boolean {
    return !!pickupLocation.utilization?.isFull;
  }

  // A full pickup location stays selectable when it is the currently selected one or
  // the member's own location (their renewal already occupies it), so that switching
  // away and back is possible.
  function isSelectable(pickupLocation: BiddingRoundPickupLocation): boolean {
    return (
      !isFull(pickupLocation) ||
      pickupLocation.id === pickupLocationId ||
      pickupLocation.id === currentPickupLocationId
    );
  }

  function isOwnFullLocation(
    pickupLocation: BiddingRoundPickupLocation,
  ): boolean {
    return (
      isFull(pickupLocation) && pickupLocation.id === currentPickupLocationId
    );
  }

  function buildMapPopupContent(pickupLocation: BiddingRoundPickupLocation) {
    return (
      <div
        className={"d-flex flex-column gap-1 align-items-center text-center"}
      >
        <strong>{pickupLocation.name}</strong>
        {buildChargeLabel(pickupLocation)}
        {buildFullIndicator(pickupLocation)}
        <div>
          {formatAddress(
            pickupLocation.street,
            pickupLocation.street2,
            pickupLocation.postcode,
            pickupLocation.city,
          )}
        </div>
        <div>{formatOpeningTimes(pickupLocation)}</div>
        <TapirButton
          size={"sm"}
          text={"Auswählen"}
          icon={
            pickupLocation.id === pickupLocationId
              ? "select_check_box"
              : "check_box_outline_blank"
          }
          variant={BUTTON_VARIANT}
          disabled={!isSelectable(pickupLocation)}
          onClick={() => selectLocation(pickupLocation.id!)}
        />
      </div>
    );
  }

  return (
    <>
      <div
        className={"d-flex flex-column gap-2"}
        style={{ width: "100%", flexGrow: 1 }}
      >
        {texts.pickupLocationText && (
          <p
            className={"text-center mb-0"}
            dangerouslySetInnerHTML={{ __html: texts.pickupLocationText }}
          />
        )}

        <ButtonGroup style={{ width: "100%" }}>
          {(["map", "list"] as PickupLocationTab[]).map((tab) => (
            <ToggleButton
              key={tab}
              id={"bidding_round_pickup_tab_" + tab}
              value={tab}
              type={"radio"}
              variant={BUTTON_VARIANT}
              name={"bidding_round_pickup_tabs"}
              checked={currentTab === tab}
              onChange={() => setCurrentTab(tab)}
              style={{ width: "100%" }}
            >
              {getTabName(tab)}
            </ToggleButton>
          ))}
        </ButtonGroup>

        {currentTab === "map" && stepActive && (
          <div style={{ position: "relative", height: "45dvh", width: "100%" }}>
            <MapContainer
              center={[
                Number.parseFloat(pickupLocations[0]?.coordsLon ?? "10"),
                Number.parseFloat(pickupLocations[0]?.coordsLat ?? "51"),
              ]}
              zoom={12}
              scrollWheelZoom={true}
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                right: 0,
                left: 0,
              }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                referrerPolicy={"no-referrer-when-downgrade"}
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {pickupLocations.map((pickupLocation) => (
                <Marker
                  position={[
                    Number.parseFloat(pickupLocation.coordsLon),
                    Number.parseFloat(pickupLocation.coordsLat),
                  ]}
                  icon={L.icon({
                    iconUrl:
                      "/static/subscriptions/" + getMarkerIcon(pickupLocation),
                    shadowUrl: "/static/subscriptions/marker-shadow.png",
                    iconAnchor: [13, 35],
                    popupAnchor: [0, -33],
                  })}
                  key={pickupLocation.id}
                >
                  <Popup>{buildMapPopupContent(pickupLocation)}</Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        )}

        {currentTab === "list" && (
          <ListGroup style={{ maxHeight: "50dvh", overflow: "scroll" }}>
            {pickupLocations
              .toSorted((a, b) => a.name.localeCompare(b.name))
              .map((pickupLocation) => (
                <ListGroupItem
                  key={pickupLocation.id}
                  style={{ cursor: "pointer", lineHeight: "1.1rem" }}
                  className={
                    pickupLocation.id === pickupLocationId ? "active" : ""
                  }
                  onClick={() => {
                    if (isSelectable(pickupLocation)) {
                      void selectLocation(pickupLocation.id!);
                    }
                  }}
                >
                  <small>
                    <strong>{pickupLocation.name}</strong>
                    <br />
                    {buildChargeLabel(pickupLocation)}
                    {pickupLocation.utilization && (
                      <>
                        <br />
                        <small
                          className={
                            pickupLocation.utilization.isFull
                              ? "text-danger"
                              : "text-muted"
                          }
                        >
                          {pickupLocation.utilization.fillPercent !== null
                            ? interpolate("Auslastung: {percent}%", {
                                percent:
                                  pickupLocation.utilization.fillPercent.toFixed(
                                    0,
                                  ),
                              })
                            : "Auslastung unbekannt"}
                        </small>
                      </>
                    )}
                    <br />
                    <small>
                      {formatAddress(
                        pickupLocation.street,
                        pickupLocation.street2,
                        pickupLocation.postcode,
                        pickupLocation.city,
                      )}
                    </small>
                    <br />
                    <small>{formatOpeningTimes(pickupLocation)}</small>
                  </small>
                </ListGroupItem>
              ))}
          </ListGroup>
        )}

        <Form.Group>
          <Form.Label>{"Verteilstation"}</Form.Label>
          <Form.Select
            value={pickupLocationId}
            onChange={(event) => void selectLocation(event.target.value)}
          >
            <option value={""}>–</option>
            {pickupLocations.map((pickupLocation) => (
              <option
                key={pickupLocation.id}
                value={pickupLocation.id!}
                disabled={!isSelectable(pickupLocation)}
              >
                {pickupLocation.name}
                {pickupLocation.utilization?.isFull ? " (ausgelastet)" : ""}
              </option>
            ))}
          </Form.Select>
          {capacityError && (
            <div className={"text-danger small"}>{capacityError}</div>
          )}
        </Form.Group>
      </div>

      <NextStepButton
        onClick={validate}
        showError={showValidation && !pickupLocationId}
        text={
          showValidation && !pickupLocationId
            ? "Noch keine Verteilstation ausgewählt"
            : undefined
        }
        stepActive={stepActive}
      />
    </>
  );
};

export default BiddingRoundPickupLocationStep;
