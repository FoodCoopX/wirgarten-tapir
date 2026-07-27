import {
  CategoryScale,
  ChartData,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import dayjs from "dayjs";
import React, { useEffect, useState } from "react";
import { Alert, Card, Form, Spinner } from "react-bootstrap";
import { Line } from "react-chartjs-2";
import { AssociationsApi, type GraphDataset } from "../api-client";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AdminDashboardAssociationDataProps {
  csrfToken: string;
}

const AdminDashboardAssociationData: React.FC<
  AdminDashboardAssociationDataProps
> = ({ csrfToken }) => {
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
      setInputError("Ungültiges Start-Datum: " + startDateAsString);
      return;
    }

    const endDate = new Date(endDateAsString);
    if (Number.isNaN(endDate.valueOf())) {
      setInputError("Ungültiges End-Datum: " + endDateAsString);
      return;
    }

    api
      .associationsApiNumberOfAssociationMembersPerMonthRetrieve({
        startDate: startDate,
        endDate: endDate,
      })
      .then((data) => {
        setLabels(data.labels);
        setDatasets(data.datasets);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Anzahl an Mitglieder",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [startDateAsString, endDateAsString]);

  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
  );

  const POINT_STYLES = ["circle", "cross", "crossRot", "dash"];

  function buildData(): ChartData<"line"> {
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
          <div className={"d-flex justify-content-between align-items-center"}>
            <Card.Title className={"mb-0"}>Anzahl an Mitglieder</Card.Title>
            <div className={"d-flex gap-2"}>
              <Form.Control
                type={"date"}
                value={startDateAsString}
                onChange={(event) => setStartDateAsString(event.target.value)}
              />
              <Form.Control
                type={"date"}
                value={endDateAsString}
                onChange={(event) => setEndDateAsString(event.target.value)}
              />
            </div>
          </div>
        </Card.Header>
        <Card.Body>
          {inputError && <Alert variant={"warning"}>{inputError}</Alert>}
          {loading ? (
            <Spinner />
          ) : (
            <Line
              style={{ minWidth: "500px" }}
              data={buildData()}
              options={{
                responsive: true,
                scales: { y: { suggestedMin: 0 } },
              }}
            />
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

export default AdminDashboardAssociationData;
