import React, { useEffect, useState } from "react";
import { TapirTheme } from "../types/TapirTheme.ts";
import { PublicProductType } from "../api-client";
import { sortProductTypes } from "./sortProductTypes.ts";
import { Form } from "react-bootstrap";

interface BestellWizardIntroProps {
  theme: TapirTheme;
  selectedProductTypes: PublicProductType[];
  setSelectedProductTypes: (selectedProductTypes: PublicProductType[]) => void;
  publicProductTypes: PublicProductType[];
}

const BestellWizardIntro: React.FC<BestellWizardIntroProps> = ({
  theme,
  selectedProductTypes,
  setSelectedProductTypes,
  publicProductTypes,
}) => {
  const [investingMembership, setInvestingMembership] = useState(false);

  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  useEffect(() => {
    if (investingMembership) {
      setSelectedProductTypes([]);
    }
  }, [investingMembership]);

  useEffect(() => {
    if (selectedProductTypes.length > 0) {
      setInvestingMembership(false);
    }
  }, [selectedProductTypes]);

  function updateProductSelection(
    productType: PublicProductType,
    checked: boolean,
  ) {
    if (checked) {
      selectedProductTypes.push(productType);
    } else {
      selectedProductTypes = selectedProductTypes.filter(
        (existingType) => existingType.id !== productType.id,
      );
    }
    setSelectedProductTypes([...sortProductTypes(selectedProductTypes)]);
  }

  return (
    <>
      <h1 className={"text-center"}>Mitmachen im Biotop</h1>
      <p>
        Du möchtest Teil des Biotops werden? Dann gibt es jetzt verschiedene
        Möglichkeiten:
      </p>
      <p>
        Das Biotop Oberland ist eine Genossenschaft. Es gehört allen
        Mitgliedern, und nur Mitglieder können weitere Verträge abschließen und
        damit Gemüse beziehen oder vergünstigt im Hofpunkt einkaufen.
      </p>
      <p>
        Du bist bereits Mitglied? Dann schließe bitte weitere Verträge über
        deinen persönlichen <a href={"/"}>Mitglieder-Bereich</a> ab.
      </p>
      <h3>Welche Mitgliedschaft(en) möchtest du?</h3>
      <div className={"d-flex flex-column gap-3"}>
        {publicProductTypes.map((publicProductType) => (
          <div key={publicProductType.id}>
            <Form.Check
              id={publicProductType.id}
              label={publicProductType.name}
              onChange={(event) =>
                updateProductSelection(publicProductType, event.target.checked)
              }
              checked={selectedProductTypes.includes(publicProductType)}
            />
            <span>
              {!publicProductType.descriptionBestellwizardShort ? (
                "No description"
              ) : (
                <span
                  dangerouslySetInnerHTML={getHtmlDescription(
                    publicProductType.descriptionBestellwizardShort,
                  )}
                ></span>
              )}
            </span>
          </div>
        ))}
        <div>
          <Form.Check
            id={"investingMembership"}
            label={"Fördermitgliedschaft in Genossenschaft"}
            onChange={(event) => setInvestingMembership(event.target.checked)}
            checked={investingMembership}
          />
          <span>
            Werde Teil des Biotops und unterstütze die Genossenschaft als
            Fördermitglied der Genossenschaft ohne weiteren Vertrag.
          </span>
        </div>
      </div>
    </>
  );
};

export default BestellWizardIntro;
