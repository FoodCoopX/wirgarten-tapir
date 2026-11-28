import React, { useEffect, useState } from "react";
import { Modal, Table } from "react-bootstrap";
import { EmailDispatch, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../contexts/alerts";
import { useApi } from "../hooks/useApi";
import { formatDate } from "../utils/formatDate";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination";
import DispatchErrorMessage from "./DispatchErrorMessage";
import TapirPagination from "./TapirPagination";
import Loading from "./loading";

interface DispatchErrorDetailsModalProps {
  open: boolean;
  onClose: () => void;
  recipient: string;
  startDate?: Date;
  endDate?: Date;
}

const DispatchErrorDetailsModal: React.FC<DispatchErrorDetailsModalProps> = ({
  open,
  onClose,
  recipient,
  startDate,
  endDate,
}) => {
  const [emailDispatches, setEmailDispatches] = useState<EmailDispatch[]>([]);
  const [dispatchCount, setDispatchCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const emailDispatchApi = useApi(TapirmailApi);
  const showAlert = useAlert();

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [startDate, endDate, recipient, open, currentPage]);

  function loadData() {
    if (!open) return;

    setLoading(true);
    emailDispatchApi
      .tapirmailApiEmailDispatchGetFailedDispatchesList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
        startDate: startDate,
        endDate: endDate,
        recipient: recipient,
      })
      .then((paginatedData) => {
        setEmailDispatches(paginatedData.results ?? []);
        setDispatchCount(paginatedData.count ?? 0);
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Dispatches", "danger");
      })
      .finally(() => setLoading(false));
  }

  function renderDetails(dispatch: EmailDispatch) {
    switch (dispatch.dispatchStatus) {
      case "bounced":
        return (
          <span>
            Bounce-Typ "{dispatch.bounceType}" mit Nachricht :{" "}
            {dispatch.bounceMessage}
          </span>
        );
      case "error":
        return <DispatchErrorMessage errorMessage={dispatch.errorMessage} />;
      case "opened":
        return <span>Geöffnet am {formatDate(dispatch.openedTime)}</span>;
      case "unknown":
        return <span></span>;
    }
  }

  return (
    <Modal show={open} onHide={onClose} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>Versand Fehler Details</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {emailDispatches.length > 0 && (
          <>Details für {emailDispatches[0].recipient} </>
        )}
        {startDate && <>von {formatDate(startDate)} </>}
        {endDate && <>bis {formatDate(endDate)}</>}
        <hr />
        {loading ? (
          <Loading />
        ) : (
          <Table striped hover style={{ margin: "0" }}>
            <thead>
              <tr>
                <th>Versand Datum</th>
                <th>Fehler Details</th>
              </tr>
            </thead>
            <tbody>
              {emailDispatches.map((dispatch: EmailDispatch) => (
                <tr key={dispatch.id}>
                  <td>{formatDate(dispatch.sentTime)}</td>
                  <td>{renderDetails(dispatch)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Modal.Body>
      {dispatchCount > DEFAULT_PAGE_SIZE && (
        <Modal.Footer className="d-flex justify-content-center align-items-center">
          <TapirPagination
            pageSize={DEFAULT_PAGE_SIZE}
            currentPage={currentPage}
            goToPage={setCurrentPage}
            itemCount={dispatchCount}
          />
        </Modal.Footer>
      )}
    </Modal>
  );
};

export default DispatchErrorDetailsModal;
