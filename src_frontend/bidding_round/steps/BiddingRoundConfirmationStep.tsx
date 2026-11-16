import React from "react";
import { Button } from "react-bootstrap";

interface BiddingRoundConfirmationStepProps {
  contentHtml: string;
  onEdit: () => void;
}

const BiddingRoundConfirmationStep: React.FC<
  BiddingRoundConfirmationStepProps
> = ({ contentHtml, onEdit }) => {
  return (
    <>
      <div
        className={"text-center"}
        dangerouslySetInnerHTML={{ __html: contentHtml }}
      />
      <div className={"d-flex justify-content-center"}>
        <Button variant={"outline-dark"} onClick={onEdit}>
          Gebot ändern
        </Button>
      </div>
    </>
  );
};

export default BiddingRoundConfirmationStep;
