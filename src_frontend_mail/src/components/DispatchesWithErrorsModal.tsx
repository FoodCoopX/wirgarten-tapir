import React, { useEffect, useState } from "react";
import { Form, Modal, Table } from "react-bootstrap";
import { GroupedEmailDispatch, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../contexts/alerts";
import { useApi } from "../hooks/useApi";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination";
import DateTimePicker from "./dateTimePicker";
import DispatchErrorDetailsModal from "./DispatchErrorDetailsModal";
import Loading from "./loading";
import TapirPagination from "./TapirPagination";

interface DispatchesWithErrorsModalProps {
  open: boolean;
  onClose: () => void;
}

const DispatchesWithErrorsModal: React.FC<DispatchesWithErrorsModalProps> = ({
  open,
  onClose,
}) => {
  const [groupedDispatches, setGroupedDispatches] = useState<
    GroupedEmailDispatch[]
  >([]);
  const [groupCount, setGroupCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [startDate, setStartDate] = useState<Date | undefined>(
    getInitialStartDate(),
  );
  const [endDate, setEndDate] = useState<Date | undefined>(new Date());
  const emailDispatchApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [selectedRecipient, setSelectedRecipient] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [startDate, endDate, currentPage, open]);

  function loadData() {
    if (!open) return;

    setLoading(true);
    emailDispatchApi
      .tapirmailApiEmailDispatchRecipientsWithErrorsList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
        startDate: startDate,
        endDate: endDate,
      })
      .then((paginatedData) => {
        setGroupedDispatches(paginatedData.results ?? []);
        setGroupCount(paginatedData.count ?? 0);
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Dispatches", "danger");
      })
      .finally(() => setLoading(false));
  }

  function getInitialStartDate() {
    let d = new Date();
    d.setFullYear(d.getFullYear() - 1, d.getMonth(), d.getDate());
    return d;
  }

  function getMinDate() {
    let d = new Date();
    d.setFullYear(d.getFullYear() - 5, d.getMonth(), d.getDate());
    return d;
  }

  return (
    <>
      <Modal show={open && !selectedRecipient} onHide={onClose} centered={true}>
        <Modal.Header closeButton>
          <Modal.Title>E-Mail-Adressen mit Fehler</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className={"d-flex gap-2"}>
            <Form.Group>
              <Form.Label>Von</Form.Label>
              <DateTimePicker
                onChange={setStartDate}
                initialValue={getInitialStartDate()}
                minDate={getMinDate()}
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Bis</Form.Label>
              <DateTimePicker
                onChange={setEndDate}
                initialValue={new Date()}
                minDate={getMinDate()}
              />
            </Form.Group>
          </div>
          {loading ? (
            <Loading />
          ) : (
            <Table striped hover style={{ margin: "0" }}>
              <thead>
                <tr>
                  <th>Adresse</th>
                  <th>Anzahl an Fehler</th>
                </tr>
              </thead>
              <tbody>
                {groupedDispatches.map((group) => (
                  <tr
                    key={group.recipient}
                    onClick={() => {
                      setSelectedRecipient(group.recipient);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <td>{group.recipient}</td>
                    <td style={{ textAlign: "right" }}>{group.count}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Modal.Body>
        {groupCount > DEFAULT_PAGE_SIZE && (
          <Modal.Footer className="d-flex justify-content-center align-items-center">
            <TapirPagination
              pageSize={DEFAULT_PAGE_SIZE}
              currentPage={currentPage}
              goToPage={setCurrentPage}
              itemCount={groupCount}
            />
          </Modal.Footer>
        )}
      </Modal>
      {selectedRecipient && (
        <DispatchErrorDetailsModal
          open={!!selectedRecipient}
          onClose={() => setSelectedRecipient("")}
          recipient={selectedRecipient}
          startDate={startDate}
          endDate={endDate}
        />
      )}
    </>
  );
};

export default DispatchesWithErrorsModal;
