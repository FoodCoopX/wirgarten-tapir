import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { Accordion, AccordionBody } from "react-bootstrap";
import { GenericIntroContent } from "../types/GenericIntroContent.ts";

interface StepGenericIntroProps {
  content: GenericIntroContent;
  goToNextStep: () => void;
}

const StepGenericIntro: React.FC<StepGenericIntroProps> = ({
  content,
  goToNextStep,
}) => {
  return (
    <>
      <div
        style={{ height: "80dvh", display: "flex", flexDirection: "column" }}
        className={"d-flex flex-column gap-2 mx-2"}
      >
        <div
          style={{
            maxHeight: "70dvh",
            overflowY: "scroll",
          }}
        >
          <div
            className={
              "d-flex align-items-center justify-content-center gap-2 flex-column"
            }
            style={{ minHeight: "70dvh" }}
          >
            <h1 className={"text-center"}>{content.title}</h1>
            <div>
              {content.text && (
                <p
                  className={"text-center"}
                  dangerouslySetInnerHTML={getHtmlDescription(content.text)}
                />
              )}
              <div className={"d-flex flex-column gap-2"}>
                {content.accordions &&
                  content.accordions.length > 0 &&
                  content.accordions.map((accordion) => (
                    <Accordion>
                      <Accordion.Item
                        key={accordion.order}
                        eventKey={accordion.order.toString()}
                      >
                        <Accordion.Header>{accordion.title}</Accordion.Header>
                        <AccordionBody>
                          <div
                            style={{ background: "transparent" }}
                            dangerouslySetInnerHTML={getHtmlDescription(
                              accordion.description,
                            )}
                          />
                        </AccordionBody>
                      </Accordion.Item>
                    </Accordion>
                  ))}
              </div>
            </div>
          </div>
        </div>
        <div className={"d-flex flex-row justify-content-center"}>
          <TapirButton
            variant={"outline-secondary"}
            text={"Weiter"}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
          />
        </div>
      </div>
    </>
  );
};

export default StepGenericIntro;
