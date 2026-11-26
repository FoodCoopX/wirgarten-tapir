import React from "react";
import { Badge } from "react-bootstrap";
import { EmailConfigurationVersionStatusEnum } from "tapir-api-client";
import { EMAIL_CONFIGURATION_VERSION_STATUS_PROPS } from "../utils/emailConfigurationVersionStatusProps";

interface EmailConfigurationVersionStatusBadgeProps {
  status: EmailConfigurationVersionStatusEnum;
}

const EmailConfigurationVersionStatusBadge: React.FC<
  EmailConfigurationVersionStatusBadgeProps
> = ({ status }) => {
  const props = EMAIL_CONFIGURATION_VERSION_STATUS_PROPS[status];
  return (
    <Badge bg={props.color} pill={true}>
      {props.text}
    </Badge>
  );
};

export default EmailConfigurationVersionStatusBadge;
