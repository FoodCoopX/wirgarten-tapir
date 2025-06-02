import React, { useEffect, useState } from "react";
import { Col, Form, Row } from "react-bootstrap";
import { type PublicProductType, SubscriptionsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface BestellWizardIntroBiotopProps {}

const BestellWizardIntroBiotop: React.FC<
  BestellWizardIntroBiotopProps
> = () => {
  const subscriptionsApi = useApi(SubscriptionsApi, "invalid");
  const [publicProductTypes, setPublicProductTypes] = useState<
    PublicProductType[]
  >([]);

  useEffect(() => {
    subscriptionsApi
      .subscriptionsPublicProductTypesList()
      .then(setPublicProductTypes)
      .catch(handleRequestError);
  }, []);

  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  return (
    <Row className={"justify-content-center"}>
      <Col sm={"10"}>
        <h1 className={"text-center"}>Mitmachen im Biotop</h1>
        <p>
          Du möchtest Teil des Biotops werden? Dann gibt es jetzt verschiedene
          Möglichkeiten:
        </p>
        <p>
          Das Biotop Oberland ist eine Genossenschaft. Es gehört allen
          Mitgliedern, und nur Mitglieder können weitere Verträge abschließen
          und damit Gemüse beziehen oder vergünstigt im Hofpunkt einkaufen.
        </p>
        <p>
          Du bist bereits Mitglied? Dann schließe bitte weitere Verträge über
          deinen persönlichen <a href={"/"}>Mitglieder-Bereich</a> ab.
        </p>
        <h3>Welche Mitgliedschaft(en) möchtest du?</h3>
        <div className={"d-flex flex-column gap-3"}>
          {publicProductTypes.map((publicProductType) => (
            <div key={publicProductType.id}>
              <Form.Check label={publicProductType.name} />
              <span>
                {!publicProductType.descriptionBestellwizard ? (
                  "No description"
                ) : (
                  <span
                    dangerouslySetInnerHTML={getHtmlDescription(
                      publicProductType.descriptionBestellwizard,
                    )}
                  ></span>
                )}
              </span>
            </div>
          ))}
          <div>
            <Form.Check label={"Fördermitgliedschaft in Genossenschaft"} />
            <span>
              Werde Teil des Biotops und unterstütze die Genossenschaft als
              Fördermitglied der Genossenschaft ohne weiteren Vertrag.
            </span>
          </div>
        </div>
      </Col>
    </Row>
  );
};

export default BestellWizardIntroBiotop;
