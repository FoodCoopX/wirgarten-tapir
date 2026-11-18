import dayjs from "dayjs";
import "dayjs/locale/de";
import React, { useState } from "react";
import { Accordion, Modal, Spinner, Table } from "react-bootstrap";
import { CoreApi, type MemberDataDisclosure } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface MemberDataDisclosureButtonProps {
  memberId: string;
  csrfToken: string;
}

const MemberDataDisclosureButton: React.FC<MemberDataDisclosureButtonProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [data, setData] = useState<MemberDataDisclosure | null>(null);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function onShow() {
    setShow(true);
    if (data || loading) {
      return;
    }
    setLoading(true);
    api
      .coreApiMemberDataDisclosureRetrieve({ memberId: memberId })
      .then(setData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der gespeicherten Daten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function pdfUrl() {
    const parameters = new URLSearchParams({ member_id: memberId });
    return `/core/api/member_data_disclosure_pdf?${parameters}`;
  }

  function formatDate(date: Date | null | undefined) {
    return date ? dayjs(date).locale("de").format("DD.MM.YYYY") : "–";
  }

  return (
    <>
      <TapirButton
        variant={"outline-secondary"}
        icon={"help"}
        size={"sm"}
        tooltip={"Was wird über mich gespeichert?"}
        onClick={onShow}
      />
      <Modal show={show} onHide={() => setShow(false)} size={"lg"} centered>
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>Meine Daten</h5>
        </Modal.Header>
        <Modal.Body>
          <p>
            Hier siehst du, welche Daten über dich gespeichert sind, wofür wir
            sie brauchen und wie lange wir sie aufbewahren.
          </p>
          {loading && <Spinner size={"sm"} />}
          {data && (
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
        </Modal.Body>
        <Modal.Footer>
          <a className={"btn btn-outline-primary"} href={pdfUrl()} download>
            <span className={"material-icons"}>print</span> Als PDF
          </a>
        </Modal.Footer>
      </Modal>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MemberDataDisclosureButton;
