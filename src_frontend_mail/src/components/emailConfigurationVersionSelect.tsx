import { Badge, Dropdown, Form } from "react-bootstrap";
import {
  EmailConfigurationVersion,
  EmailConfigurationVersionStatusEnum,
} from "tapir-api-client";
import { EMAIL_CONFIGURATION_VERSION_STATUS_PROPS } from "../utils/emailConfigurationVersionStatusProps";
import { formatDate } from "../utils/formatDate";

const EmailConfigurationVersionSelect = ({
  versions,
  selectedVersionId,
  onChange,
}: {
  versions: EmailConfigurationVersion[];
  selectedVersionId: string;
  onChange: (version: string) => void;
}) => {
  const handleSelect = (key: any, event: any) => {
    onChange(key);
  };

  const selectedVersion: EmailConfigurationVersion | undefined =
    versions.find((v) => v.id === selectedVersionId) || undefined;
  return (
    <div>
      <Form>
        <Form.Group controlId="exampleForm.SelectCustom">
          <Dropdown onSelect={handleSelect}>
            <Dropdown.Toggle
              style={{ width: "100%" }}
              variant={
                "outline-" +
                (selectedVersion
                  ? EMAIL_CONFIGURATION_VERSION_STATUS_PROPS[
                      (selectedVersion!!.status ||
                        "draft") as EmailConfigurationVersionStatusEnum
                    ].color
                  : "primary")
              }
              id="dropdown-custom-components"
            >
              {selectedVersion
                ? `${
                    EMAIL_CONFIGURATION_VERSION_STATUS_PROPS[
                      selectedVersion.status!! as EmailConfigurationVersionStatusEnum
                    ].text
                  } ${formatDate(selectedVersion.updatedAt)}`
                : "Select version"}
            </Dropdown.Toggle>
            <Dropdown.Menu style={{ width: "100%", textAlign: "center" }}>
              {versions.map((v: EmailConfigurationVersion) => (
                <Dropdown.Item key={v.id} eventKey={v.id}>
                  <Badge
                    bg={
                      EMAIL_CONFIGURATION_VERSION_STATUS_PROPS[
                        (v.status ||
                          "draft") as EmailConfigurationVersionStatusEnum
                      ].color
                    }
                  >
                    {
                      EMAIL_CONFIGURATION_VERSION_STATUS_PROPS[
                        (v.status ||
                          "draft") as EmailConfigurationVersionStatusEnum
                      ].text
                    }
                  </Badge>{" "}
                  {formatDate(v.updatedAt)}
                </Dropdown.Item>
              ))}
            </Dropdown.Menu>
          </Dropdown>
        </Form.Group>
      </Form>
    </div>
  );
};

export default EmailConfigurationVersionSelect;
