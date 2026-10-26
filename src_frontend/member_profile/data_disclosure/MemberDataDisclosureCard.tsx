import dayjs from "dayjs";
import "dayjs/locale/de";
import React, { useState } from "react";
import { Accordion, Button, Card, Spinner, Table } from "react-bootstrap";
import { CoreApi, type MemberDataDisclosure } from "../../api-client";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface MemberDataDisclosureCardProps {
  memberId: string;
  csrfToken: string;
}

const MemberDataDisclosureCard: React.FC<MemberDataDisclosureCardProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [data, setData] = useState<MemberDataDisclosure | null>(null);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function loadData() {
    setLoading(true);
    api
      .coreApiMemberDataDisclosureRetrieve({ memberId: memberId })
      .then((loadedData) => {
        setData(loadedData);
        setVisible(true);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der gespeicherten Daten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function onToggle() {
    if (visible) {
      setVisible(false);
      return;
    }
    loadData();
  }

  function downloadUrl(fileType: "json" | "pdf") {
    const parameters = new URLSearchParams({
      member_id: memberId,
      file_type: fileType,
    });
    return `/core/api/member_data_disclosure_download?${parameters}`;
  }

  function formatDate(date: Date | null | undefined) {
    return date ? dayjs(date).locale("de").format("DD.MM.YYYY") : "–";
  }

  return (
    <>
      <Card>
        <Card.Header>
          <h5 className={"mb-0"}>Gespeicherte Daten</h5>
        </Card.Header>
        <Card.Body>
          <p>
            Hier siehst du, welche Daten über dich gespeichert sind, wofür wir
            sie brauchen und wie lange wir sie aufbewahren.
          </p>
          <div className={"d-flex flex-wrap gap-2 mb-3"}>
            <Button
              variant={"outline-primary"}
              onClick={onToggle}
              disabled={loading}
            >
              {loading ? (
                <Spinner size={"sm"} />
              ) : (
                <span className={"material-icons"}>
                  {visible ? "visibility_off" : "visibility"}
                </span>
              )}{" "}
              {visible ? "Daten verbergen" : "Daten anzeigen"}
            </Button>
            <a
              className={"btn btn-outline-primary"}
              href={downloadUrl("pdf")}
              download
            >
              <span className={"material-icons"}>print</span> Als PDF
            </a>
            <a
              className={"btn btn-outline-primary"}
              href={downloadUrl("json")}
              download
            >
              <span className={"material-icons"}>data_object</span> Als JSON
            </a>
          </div>
          {data && visible && (
            <>
              <p className={"text-muted small"}>
                Stand:{" "}
                {dayjs(data.generatedAt)
                  .locale("de")
                  .format("DD.MM.YYYY HH:mm")}
              </p>
              <Accordion alwaysOpen>
                {data.sections.map((section) => (
                  <Accordion.Item key={section.key} eventKey={section.key}>
                    <Accordion.Header>
                      {section.title}
                      {section.records.length === 0 && (
                        <span className={"text-muted ms-2 small"}>
                          (keine Daten)
                        </span>
                      )}
                    </Accordion.Header>
                    <Accordion.Body>
                      <p className={"small text-muted"}>
                        Zweck: {section.purpose}
                        <br />
                        Aufbewahrung: {section.retention}
                      </p>
                      {section.records.map((record, index) => (
                        <Table key={index} size={"sm"} bordered>
                          <tbody>
                            {record.map((field) => (
                              <tr key={field.name}>
                                <th className={"w-50 fw-normal"}>
                                  {field.label}
                                </th>
                                <td>{field.value ?? "–"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </Table>
                      ))}
                    </Accordion.Body>
                  </Accordion.Item>
                ))}
                <Accordion.Item eventKey={"log"}>
                  <Accordion.Header>Protokoll (Übersicht)</Accordion.Header>
                  <Accordion.Body>
                    <p className={"small text-muted"}>
                      Änderungen und Vorgänge zu deinem Konto. Hier steht nur,
                      wie viele Einträge es gibt, nicht ihr Inhalt.
                    </p>
                    {data.logOverview.length === 0 ? (
                      <p>Keine Einträge.</p>
                    ) : (
                      <Table size={"sm"} bordered>
                        <tbody>
                          {data.logOverview.map((entry) => (
                            <tr key={entry.type}>
                              <th className={"w-50 fw-normal"}>{entry.type}</th>
                              <td>
                                {entry.count}x, {formatDate(entry.first)} bis{" "}
                                {formatDate(entry.last)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    )}
                  </Accordion.Body>
                </Accordion.Item>
                <Accordion.Item eventKey={"mails"}>
                  <Accordion.Header>Versendete E-Mails</Accordion.Header>
                  <Accordion.Body>
                    <p className={"small text-muted"}>
                      Nur die Übersicht, nicht der Inhalt der Mails.
                    </p>
                    {data.mailOverview.count === 0 ? (
                      <p>Keine E-Mails gespeichert.</p>
                    ) : (
                      <p>
                        {data.mailOverview.count} E-Mails,{" "}
                        {formatDate(data.mailOverview.first)} bis{" "}
                        {formatDate(data.mailOverview.last)}
                      </p>
                    )}
                  </Accordion.Body>
                </Accordion.Item>
              </Accordion>
            </>
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

export default MemberDataDisclosureCard;
