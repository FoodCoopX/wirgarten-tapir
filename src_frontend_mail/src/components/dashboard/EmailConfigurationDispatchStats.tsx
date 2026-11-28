import React from "react";
import { ProgressBar } from "react-bootstrap";
import { EmailConfigurationDispatch } from "tapir-api-client";

export const EmailConfigurationDispatchStats: React.FC<{
  emailConfigurationDispatch: EmailConfigurationDispatch;
}> = ({ emailConfigurationDispatch }) => {
  return (
    <span>
      <small>
        <strong>
          {emailConfigurationDispatch.sentCount
            ? Math.round(
                (emailConfigurationDispatch.openedCount /
                  emailConfigurationDispatch.sentCount) *
                  100,
              )
            : 0}
          &nbsp;%
        </strong>
        &nbsp;&nbsp;&nbsp;(
        <strong>{emailConfigurationDispatch.openedCount}</strong>/
        <span style={{ color: "darkred" }}>
          {emailConfigurationDispatch.errorCount}
        </span>
        /{emailConfigurationDispatch.sentCount})
      </small>
      <ProgressBar style={{ height: "0.75em" }}>
        <ProgressBar
          title={"Geöffnet: " + emailConfigurationDispatch.openedCount}
          variant="success"
          now={emailConfigurationDispatch.openedCount * 100}
        />
        <ProgressBar
          title={"Fehler: " + emailConfigurationDispatch.errorCount}
          variant="danger"
          now={emailConfigurationDispatch.errorCount * 100}
        />
        <ProgressBar
          title={"Zugestellt: " + emailConfigurationDispatch.deliveredCount}
          variant="primary"
          now={emailConfigurationDispatch.deliveredCount * 100}
        />

        <ProgressBar
          title={
            "Nicht geöffnet: " +
            (emailConfigurationDispatch.sentCount -
              emailConfigurationDispatch.openedCount -
              emailConfigurationDispatch.errorCount -
              emailConfigurationDispatch.deliveredCount)
          }
          variant="warning"
          now={
            (emailConfigurationDispatch.sentCount -
              emailConfigurationDispatch.openedCount -
              emailConfigurationDispatch.errorCount -
              emailConfigurationDispatch.deliveredCount) *
            100
          }
        />
      </ProgressBar>
    </span>
  );
};

export default EmailConfigurationDispatchStats;
