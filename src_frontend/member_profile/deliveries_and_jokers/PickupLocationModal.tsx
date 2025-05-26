import React from "react";
import { Modal } from "react-bootstrap";
import { PickupLocation, PickupLocationOpeningTime } from "../../api-client";
import dayjs from "dayjs";

interface PickupLocationModalProps {
  pickupLocation: PickupLocation;
  openingTimes: PickupLocationOpeningTime[];
  onHide: () => void;
}

const PickupLocationModal: React.FC<PickupLocationModalProps> = ({
  pickupLocation,
  openingTimes,
  onHide,
}) => {
  return (
    <Modal onHide={onHide} show={true} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h4>{pickupLocation.name}</h4>
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>
          {pickupLocation.street}
          <br />
          {pickupLocation.street2 && (
            <>
              {pickupLocation.street2}
              <br />
            </>
          )}
          {pickupLocation.postcode} {pickupLocation.city}
          <br />
        </p>
        <p>
          {pickupLocation.info && (
            <>
              Information: {pickupLocation.info}
              <br />
            </>
          )}
          {pickupLocation.accessCode && (
            <>
              Zugangscode: {pickupLocation.accessCode}
              <br />
            </>
          )}
          {pickupLocation.messengerGroupLink && (
            <>
              Signal Gruppe:{" "}
              <a href={pickupLocation.messengerGroupLink}>
                {pickupLocation.messengerGroupLink}
              </a>
              <br />
            </>
          )}
          {pickupLocation.contactName && (
            <>
              Kontakt: {pickupLocation.contactName}
              <br />
            </>
          )}
        </p>
        <p>
          <h5>Abholtage</h5>
          <ul>
            {openingTimes.map((openingTime) => {
              return (
                <li key={openingTime.dayOfWeek + " " + openingTime.openTime}>
                  {dayjs()
                    .day(openingTime.dayOfWeek + 1)
                    .format("dddd")}
                  : {openingTime.openTime.slice(0, 5)} bis{" "}
                  {openingTime.closeTime.slice(0, 5)} Uhr
                </li>
              );
            })}
          </ul>
        </p>
      </Modal.Body>
    </Modal>
  );
};

export default PickupLocationModal;
