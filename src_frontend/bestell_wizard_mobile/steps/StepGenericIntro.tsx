import React from "react";

import { Accordion, AccordionBody } from "react-bootstrap";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { GenericIntroContent } from "../types/GenericIntroContent.ts";
import { scrollIntoView } from "../utils/scrollIntoView.ts";

interface StepGenericIntroProps {
  content: GenericIntroContent;
  goToNextStep: () => void;
  stepActive: boolean;
}

const StepGenericIntro: React.FC<StepGenericIntroProps> = ({
  content,
  goToNextStep,
  stepActive,
}) => {
  return (
    <>
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
              <Accordion key={accordion.order}>
                <Accordion.Item
                  eventKey={accordion.order.toString()}
                  onClick={scrollIntoView}
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
      <NextStepButton onClick={goToNextStep} stepActive={stepActive} />
    </>
  );
};

export default StepGenericIntro;
