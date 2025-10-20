import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProductType } from "../../api-client";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { Accordion, AccordionBody } from "react-bootstrap";

interface Step4AProductTypeIntroProps {
  productType: PublicProductType;
  goToNextStep: () => void;
}

const Step4AProductTypeIntro: React.FC<Step4AProductTypeIntroProps> = ({
  productType,
  goToNextStep,
}) => {
  return (
    <>
      <div
        style={{ height: "100%", overflowY: "hidden" }}
        className={
          "d-flex align-items-center justify-content-center gap-2 flex-column"
        }
      >
        <h1 className={"text-center"}>Unser {productType.name}</h1>
        <div style={{ maxHeight: "45vh", overflowY: "scroll" }}>
          {productType.descriptionBestellwizardLong && (
            <p
              className={"text-center"}
              dangerouslySetInnerHTML={getHtmlDescription(
                productType.descriptionBestellwizardLong,
              )}
            ></p>
          )}
          {productType.accordions.length > 0 && (
            <Accordion>
              {productType.accordions.map((accordion) => (
                <Accordion.Item
                  key={accordion.order}
                  eventKey={accordion.order.toString()}
                >
                  <Accordion.Header>{accordion.title}</Accordion.Header>
                  <AccordionBody>
                    <div
                      dangerouslySetInnerHTML={getHtmlDescription(
                        accordion.description,
                      )}
                    />
                  </AccordionBody>
                </Accordion.Item>
              ))}
            </Accordion>
          )}
        </div>
        <TapirButton
          variant={"outline-secondary"}
          text={"Weiter"}
          onClick={goToNextStep}
          disabled={true}
        />
      </div>
    </>
  );
};

export default Step4AProductTypeIntro;
