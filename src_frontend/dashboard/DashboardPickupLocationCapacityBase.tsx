import React, { useEffect, useState } from "react";
import { Card, Form, Spinner, Table } from "react-bootstrap";
import {
  PickupLocation,
  type PickupLocationCapacityChangePoint,
  PickupLocationsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import dayjs from "dayjs";
import "dayjs/locale/de";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import { formatDateText } from "../utils/formatDateText.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";

const DashboardPickupLocationCapacityBase: React.FC = () => {
  const api = useApi(PickupLocationsApi, "no_token");
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [baseLoading, setBaseLoading] = useState(true);
  const [selectedPickupLocation, setSelectedPickupLocation] =
    useState<PickupLocation>();
  const [dataLoading, setDataLoading] = useState(true);
  const [tableHeaders, setTableHeaders] = useState<string[]>([]);
  const [dataPoints, setDataPoints] = useState<
    PickupLocationCapacityChangePoint[]
  >([]);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  useEffect(() => {
    setBaseLoading(true);
    api
      .pickupLocationsPickupLocationsList()
      .then((data) => {
        setPickupLocations(data);
        if (data.length > 0) {
          setSelectedPickupLocation(data[0]);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstationen",
          setToastDatas,
        ),
      )
      .finally(() => setBaseLoading(false));
  }, []);

  function onPickupLocationChanged(newLocationId: string) {
    for (const pickupLocation of pickupLocations) {
      if (pickupLocation.id === newLocationId) {
        setSelectedPickupLocation(pickupLocation);
        return;
      }
    }
    alert("Unknown pickup location with ID: " + newLocationId);
  }

  useEffect(() => {
    setDataLoading(true);
    if (!selectedPickupLocation) return;

    api
      .pickupLocationsApiPickupLocationCapacityEvolutionRetrieve({
        pickupLocationId: selectedPickupLocation.id,
      })
      .then((data) => {
        setTableHeaders(data.tableHeaders);
        setDataPoints(data.dataPoints);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstation-Kapazitäten",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }, [selectedPickupLocation]);

  function pickupLocationSelect() {
    return (
      <Form.Select
        value={selectedPickupLocation?.id}
        onChange={(event) => onPickupLocationChanged(event.target.value)}
      >
        {pickupLocations.map((pickupLocation) => (
          <option key={pickupLocation.id} value={pickupLocation.id}>
            {pickupLocation.name}
          </option>
        ))}
      </Form.Select>
    );
  }

  function getDataTable() {
    return (
      <>
        <p>
          Die Tabelle zeigt wie viele Kapazitäten frei sind an der jeweiligem
          Daten. Es werden nur Änderungen gelistet.
        </p>
        <Table striped hover responsive>
          <thead>
            <tr>
              <th>KW</th>
              <th>Datum</th>
              {tableHeaders.map((header) => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataPoints.map((dataPoint) => {
              return (
                <tr key={formatDateNumeric(dataPoint.date)}>
                  <td>KW{dayjs(dataPoint.date).week()}</td>
                  <td>{formatDateText(dataPoint.date)}</td>
                  {dataPoint.values.map((value, index) => (
                    <td key={index}>{value}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </Table>
      </>
    );
  }

  return (
    <>
      <Card>
        <Card.Header>
          <div
            className={
              "d-flex flex-row justify-content-between align-items-center"
            }
          >
            <h5 className={"mb-0"}>Freiwerdende Kapazitäten</h5>
            {!baseLoading && pickupLocationSelect()}
          </div>
        </Card.Header>
        <Card.Body>{dataLoading ? <Spinner /> : getDataTable()}</Card.Body>
      </Card>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default DashboardPickupLocationCapacityBase;
