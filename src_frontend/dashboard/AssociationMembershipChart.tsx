import {
  BarController,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
  type ChartData,
} from "chart.js";
import dayjs from "dayjs";
import { useEffect, useId, useState } from "react";
import { Alert, Card, Form, Spinner } from "react-bootstrap";
import { Chart } from "react-chartjs-2";
import { AssociationsApi } from "../api-client";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

ChartJS.register(
  BarController,
  BarElement,
  CategoryScale,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
);

type ChartType = "bar" | "line";

interface AssociationMembershipChartProps {
  csrfToken: string;
  title: string;
  chartType: ChartType;
  errorMessage: string;
  loadData: keyof Pick<
    AssociationsApi,
    | "associationsApiNumberOfAssociationMembersPerMonthRetrieve"
    | "associationsApiNumberOfAssociationMembershipCancellationsPerMonthRetrieve"
    | "associationsApiNumberOfAssociationMembershipCancellationsPerMonthRelativeToCancellationRetrieve"
  >;
}

const POINT_STYLES = ["circle", "cross", "crossRot", "dash"];

export default function AssociationMembershipChart({
  csrfToken,
  title,
  chartType,
  errorMessage,
  loadData,
}: Readonly<AssociationMembershipChartProps>) {
  const dateFieldId = useId();
  const api = useApi(AssociationsApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(() =>
    dayjs().date(1).subtract(8, "month").toISOString().slice(0, 10),
  );
  const [endDate, setEndDate] = useState(() =>
    dayjs().date(31).add(8, "month").toISOString().slice(0, 10),
  );
  const [inputError, setInputError] = useState("");
  const [chartData, setChartData] = useState<ChartData<ChartType>>({
    labels: [],
    datasets: [],
  });

  useEffect(() => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (Number.isNaN(start.valueOf()) || Number.isNaN(end.valueOf())) {
      setInputError(
        Number.isNaN(start.valueOf())
          ? "Ungültiges Startdatum: " + startDate
          : "Ungültiges Enddatum: " + endDate,
      );
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setInputError("");
    api[loadData](
      { startDate: start, endDate: end },
      { signal: controller.signal },
    )
      .then(({ labels, datasets }) => {
        if (controller.signal.aborted) return;

        setChartData({
          labels,
          datasets: datasets.map((dataset, index) => ({
            label: dataset.name,
            data: dataset.values,
            borderColor: dataset.color,
            backgroundColor: dataset.color,
            pointStyle: POINT_STYLES[index % POINT_STYLES.length],
          })),
        });
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          handleRequestError(error, errorMessage, setToastDatas);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [api, loadData, errorMessage, startDate, endDate]);

  return (
    <>
      <Card>
        <Card.Header>
          <div className="d-flex flex-wrap justify-content-between align-items-end gap-2">
            <Card.Title className="mb-0">{title}</Card.Title>
            <div
              className="d-grid gap-2 mw-100"
              style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}
            >
              <Form.Group controlId={dateFieldId + "-start"}>
                <Form.Label>Von</Form.Label>
                <Form.Control
                  type="date"
                  size="sm"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </Form.Group>
              <Form.Group controlId={dateFieldId + "-end"}>
                <Form.Label>Bis</Form.Label>
                <Form.Control
                  type="date"
                  size="sm"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </Form.Group>
            </div>
          </div>
        </Card.Header>
        <Card.Body>
          {inputError ? (
            <Alert variant="warning">{inputError}</Alert>
          ) : loading ? (
            <Spinner />
          ) : (
            <div
              className="position-relative w-100"
              style={{ height: "18rem" }}
            >
              <Chart
                type={chartType}
                data={chartData}
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
}
