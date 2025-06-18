import React, { useEffect, useState } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PublicProductType } from "../../api-client";
import { sortProductTypes } from "../utils/sortProductTypes.ts";
import { Form, Spinner } from "react-bootstrap";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";

interface BestellWizardIntroProps {
  theme: TapirTheme;
  selectedProductTypes: PublicProductType[];
  setSelectedProductTypes: (selectedProductTypes: PublicProductType[]) => void;
  publicProductTypes: PublicProductType[];
  allowInvestingMembership: boolean;
}

const BestellWizardIntro: React.FC<BestellWizardIntroProps> = ({
  theme,
  selectedProductTypes,
  setSelectedProductTypes,
  publicProductTypes,
  allowInvestingMembership,
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
      <BestellWizardCardTitle text={"Mitmachen im Biotop"} />
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
      <BestellWizardCardSubtitle
        text={"Welche Mitgliedschaft(en) möchtest du?"}
      />
      <div className={"d-flex flex-column gap-3"}>
        {publicProductTypes.length === 0 ? (
          <Spinner style={{ width: "10rem", height: "10rem" }} />
        ) : (
          publicProductTypes.map((publicProductType) => (
            <div key={publicProductType.id}>
              <Form.Check
                id={publicProductType.id}
                label={publicProductType.name}
                onChange={(event) =>
                  updateProductSelection(
                    publicProductType,
                    event.target.checked,
                  )
                }
                checked={selectedProductTypes.includes(publicProductType)}
                disabled={publicProductType.mustBeSubscribedTo}
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
          ))
        )}
        {allowInvestingMembership && (
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
        )}
      </div>
    </>
  );
};

export default BestellWizardIntro;
