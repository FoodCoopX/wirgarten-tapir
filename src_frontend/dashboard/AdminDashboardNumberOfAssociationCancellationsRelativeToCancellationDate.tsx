import {
  BarElement,
  CategoryScale,
  ChartData,
  Chart as ChartJS,
  Legend,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import dayjs from "dayjs";
import React, { useEffect, useId, useState } from "react";
import { Alert, Card, Form, Spinner } from "react-bootstrap";
import { Bar } from "react-chartjs-2";
import { AssociationsApi, type GraphDataset } from "../api-client";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDateProps {
  csrfToken: string;
}

const AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate: React.FC<
  AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDateProps
> = ({ csrfToken }) => {
  const dateFieldId = useId();
  const api = useApi(AssociationsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDateAsString, setStartDateAsString] = useState("");
  const [endDateAsString, setEndDateAsString] = useState("");
  const [inputError, setInputError] = useState("");
  const [labels, setLabels] = useState<string[]>([]);
  const [datasets, setDatasets] = useState<GraphDataset[]>([]);

  useEffect(() => {
    let startDate = dayjs();
    startDate = startDate.date(1);
    startDate = startDate.subtract(8, "month");
    setStartDateAsString(startDate.toISOString().slice(0, 10));

    let endDate = dayjs();
    endDate = endDate.date(31);
    endDate = endDate.add(8, "month");
    setEndDateAsString(endDate.toISOString().slice(0, 10));
  }, []);

  useEffect(() => {
    setLoading(true);
    setInputError("");

    const startDate = new Date(startDateAsString);
    if (Number.isNaN(startDate.valueOf())) {
      setInputError("Ungültiges Startdatum: " + startDateAsString);
      return;
    }

    const endDate = new Date(endDateAsString);
    if (Number.isNaN(endDate.valueOf())) {
      setInputError("Ungültiges Enddatum: " + endDateAsString);
      return;
    }

    api
      .associationsApiNumberOfAssociationMembershipCancellationsPerMonthRelativeToCancellationRetrieve(
        {
          startDate: startDate,
          endDate: endDate,
        },
      )
      .then((data) => {
        setLabels(data.labels);
        setDatasets(data.datasets);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der erfassten Kündigungen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [startDateAsString, endDateAsString]);

  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
  );

  const POINT_STYLES = ["circle", "cross", "crossRot", "dash"];

  function buildDataNumberOfMembers(): ChartData<"bar"> {
    Object.entries(datasets);
    return {
      labels,
      datasets: datasets.map((dataset, index) => {
        return {
          label: dataset.name,
          data: dataset.values,
          borderColor: dataset.color,
          backgroundColor: dataset.color,
          pointStyle: POINT_STYLES[index % POINT_STYLES.length],
        };
      }),
    };
  }

  return (
    <>
      <Card>
        <Card.Header>
          <div
            className={
              "d-flex flex-wrap justify-content-between align-items-end gap-2"
            }
          >
            <Card.Title className={"mb-0"}>
              Erfasste Kündigungen nach Monat
            </Card.Title>
            <div
              className={"d-grid gap-2 mw-100"}
              style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}
            >
              <Form.Group controlId={dateFieldId + "-start"}>
                <Form.Label>Von</Form.Label>
                <Form.Control
                  type={"date"}
                  size={"sm"}
                  value={startDateAsString}
                  onChange={(event) => setStartDateAsString(event.target.value)}
                />
              </Form.Group>
              <Form.Group controlId={dateFieldId + "-end"}>
                <Form.Label>Bis</Form.Label>
                <Form.Control
                  type={"date"}
                  size={"sm"}
                  value={endDateAsString}
                  onChange={(event) => setEndDateAsString(event.target.value)}
                />
              </Form.Group>
            </div>
          </div>
        </Card.Header>
        <Card.Body>
          {inputError && <Alert variant={"warning"}>{inputError}</Alert>}
          {loading ? (
            <Spinner />
          ) : (
            <div
              className={"position-relative w-100"}
              style={{ height: "18rem" }}
            >
              <Bar
                data={buildDataNumberOfMembers()}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: { y: { min: 0, ticks: { precision: 0 } } },
                }}
              />
            </div>
          )}
        </Card.Body>
      </Card>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default AdminDashboardNumberOfAssociationCancellationsRelativeToCancellationDate;
