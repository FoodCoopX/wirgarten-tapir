import React, { useEffect, useState } from "react";
import BestellWizardIntro from "./BestellWizardIntro.tsx";
import { TapirTheme } from "../types/tapirTheme.ts";
import { Col, Row, Spinner } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import { useApi } from "../hooks/useApi.ts";
import { CoreApi } from "../api-client";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface BestellWizardProps {
  csrfToken: string;
}

const BestellWizard: React.FC<BestellWizardProps> = ({ csrfToken }) => {
  const [theme, setTheme] = useState<TapirTheme>();
  const coreApi = useApi(CoreApi, csrfToken);

  useEffect(() => {
    coreApi
      .coreApiGetThemeRetrieve()
      .then((themeAsString) => {
        setTheme(themeAsString as TapirTheme);
      })
      .catch(handleRequestError);
  }, []);

  if (theme === undefined) {
    return (
      <Row>
        <Col>
          <Spinner />
        </Col>
      </Row>
    );
  }

  return <BestellWizardIntro theme={theme} />;
};

export default BestellWizard;
