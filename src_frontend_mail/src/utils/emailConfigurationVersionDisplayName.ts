import {
  EmailConfigurationVersion,
  EmailConfigurationVersionStatusEnum,
} from "tapir-api-client";
import { EMAIL_CONFIGURATION_VERSION_STATUS_PROPS } from "./emailConfigurationVersionStatusProps";
import { formatDate } from "./formatDate";

export function getDisplayName(version?: EmailConfigurationVersion) {
  if (!version) return "";
  return `${
    EMAIL_CONFIGURATION_VERSION_STATUS_PROPS[
      version.status!! as EmailConfigurationVersionStatusEnum
    ].text
  } ${formatDate(version.updatedAt)}`;
}
