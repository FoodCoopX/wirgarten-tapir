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
        style={{ height: "80vh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-2"}
      >
        <div
          style={{
            maxHeight: "70vh",
            overflowY: "scroll",
          }}
        >
          <div
            className={
              "d-flex align-items-center justify-content-center gap-2 flex-column"
            }
          >
            <h1 className={"text-center"}>Unser {productType.name}</h1>
            <div>
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
                  <style>
                    {`
                      .accordion *, .accordion-button:not(.collapsed) {
                        backgroundColor: transparent;
                        background: transparent;
                      }`}
                  </style>
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
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
          />
        </div>
      </div>
    </>
  );
};

export default Step4AProductTypeIntro;
