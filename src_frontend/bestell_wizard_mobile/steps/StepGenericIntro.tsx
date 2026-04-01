import React from "react";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { Accordion, AccordionBody } from "react-bootstrap";
import { GenericIntroContent } from "../types/GenericIntroContent.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { scrollIntoView } from "../utils/scrollIntoView.ts";

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
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default StepGenericIntro;
