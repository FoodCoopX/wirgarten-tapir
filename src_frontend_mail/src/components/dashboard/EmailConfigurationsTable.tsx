import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useEffect, useState } from "react";
import { Badge, Card, Form, Table } from "react-bootstrap";
import { Link } from "react-router-dom";
import {
  EmailConfiguration,
  TapirmailApi,
  TriggerDefinition,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import Paths from "../../routing";
import { EMAIL_CONFIGURATION_VERSION_STATUS_PROPS } from "../../utils/emailConfigurationVersionStatusProps";
import { formatDate } from "../../utils/formatDate";
import { DEFAULT_PAGE_SIZE } from "../../utils/pagination";
import TapirButton from "../TapirButton";
import TapirPagination from "../TapirPagination";
import Loading from "../loading";
import SelectVersionModal from "./SelectVersionModal";

interface EmailConfigurationTableProps {
  reloadConfigurations: number;
}
const EmailConfigurationTable: React.FC<EmailConfigurationTableProps> = ({
  reloadConfigurations,
}) => {
  const showAlert = useAlert();
  const [loading, setLoading] = useState(true);
  const [emailConfigurations, setEmailConfigurations] = useState<
    EmailConfiguration[]
  >([]);
  const [selectedEmailConfiguration, setSelectedEmailConfiguration] =
    useState<EmailConfiguration | null>(null);

  const [currentPage, setCurrentPage] = useState(0);
  const [configurationCount, setConfigurationCount] = useState(0);

  const [editModalOpen, setEditModalOpen] = useState(false);
  const emailConfigurationApi = useApi(TapirmailApi);
  const triggersApi = useApi(TapirmailApi);
  const [triggerDefinitions, setTriggerDefinitions] = useState<
    TriggerDefinition[]
  >([]);
  const [currentFilterTriggerId, setCurrentFilterTriggerId] = useState<
    string | undefined
  >(undefined);

  const fetchEmailConfigurations = () => {
    Promise.all([
      emailConfigurationApi.tapirmailApiEmailConfigurationFilterByTriggerList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
        triggerId:
          currentFilterTriggerId === "no_filter"
            ? undefined
            : currentFilterTriggerId,
      }),
      triggersApi.tapirmailApiTriggersList(),
    ])
      .then(([paginatedEmailConfigurationData, triggerDefinitions]) => {
        setEmailConfigurations(paginatedEmailConfigurationData.results ?? []);
        setConfigurationCount(paginatedEmailConfigurationData.count ?? 0);
        setTriggerDefinitions(triggerDefinitions);
      })
      .catch((err) => {
        console.error(err);
        showAlert("Beim Laden ist ein Fehler aufgetreten.", "danger");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    if (!emailConfigurationApi || !showAlert) return;

    fetchEmailConfigurations();
  }, [currentPage, reloadConfigurations, currentFilterTriggerId]);

  const handleSelectEmailConfiguration = (ec: EmailConfiguration) => {
    setSelectedEmailConfiguration(ec);
    setEditModalOpen(true);
  };

  const handleCloseEditModal = () => setEditModalOpen(false);

  return (
    <>
      <Card>
        <Card.Header
          as="h5"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>E-Mails</span>

          <span className={"d-flex flex-row gap-2"}>
            <Form.Select
              onChange={(event) =>
                setCurrentFilterTriggerId(event.target.value)
              }
              value={currentFilterTriggerId}
            >
              <option value={"no_filter"}>Kein Filter</option>
              {triggerDefinitions.map((triggerDefinition) => (
                <option key={triggerDefinition.id} value={triggerDefinition.id}>
                  {triggerDefinition.name}
                </option>
              ))}
            </Form.Select>
            <Link to={Paths.emailConfigurationCreate}>
              <TapirButton
                variant="primary"
                text="Neue E-Mail erstellen"
                icon={PlusCircleIcon}
              />
            </Link>
          </span>
        </Card.Header>
        <Card.Body style={{ padding: 0 }}>
          {loading ? (
            <Loading />
          ) : (
            <Table striped bordered hover>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Erstellt am</th>
                  <th>Veröffentlicht am</th>
                  <th>Letzter Entwurf aktualisiert am</th>
                </tr>
              </thead>
              <tbody>
                {emailConfigurations.map((emailConfiguration) => (
                  <tr
                    key={emailConfiguration.id}
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      handleSelectEmailConfiguration(emailConfiguration)
                    }
                  >
                    <td>{emailConfiguration.name}</td>
                    <td>{formatDate(emailConfiguration.createdAt)}</td>
                    <td>
                      {emailConfiguration.releasedDate && (
                        <Badge
                          bg={
                            EMAIL_CONFIGURATION_VERSION_STATUS_PROPS.released
                              .color
                          }
                          pill={true}
                        >
                          {formatDate(emailConfiguration.releasedDate)}
                        </Badge>
                      )}
                    </td>
                    <td>
                      {emailConfiguration.lastUpdatedDraftDate && (
                        <Badge
                          bg={
                            EMAIL_CONFIGURATION_VERSION_STATUS_PROPS.draft.color
                          }
                          pill={true}
                        >
                          {formatDate(emailConfiguration.lastUpdatedDraftDate)}
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
        {configurationCount > DEFAULT_PAGE_SIZE && (
          <Card.Footer className="d-flex justify-content-center align-items-center">
            <TapirPagination
              pageSize={DEFAULT_PAGE_SIZE}
              itemCount={configurationCount}
              currentPage={currentPage}
              goToPage={setCurrentPage}
            />
          </Card.Footer>
        )}
      </Card>
      <SelectVersionModal
        open={editModalOpen}
        emailConfiguration={selectedEmailConfiguration!!}
        onClose={handleCloseEditModal}
        onDataChanged={fetchEmailConfigurations}
      />
    </>
  );
};

export default EmailConfigurationTable;
