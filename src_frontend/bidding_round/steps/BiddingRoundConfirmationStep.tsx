import React from "react";

interface BiddingRoundConfirmationStepProps {
  contentHtml: string;
}

const BiddingRoundConfirmationStep: React.FC<
  BiddingRoundConfirmationStepProps
> = ({ contentHtml }) => {
  return (
    <div
      className={"d-flex flex-column gap-3 align-items-center"}
      style={{ width: "100%", maxWidth: "540px" }}
    >
      {contentHtml && (
        <p
          className={"text-center"}
          dangerouslySetInnerHTML={{ __html: contentHtml }}
        />
      )}
    </div>
  );
};

export default BiddingRoundConfirmationStep;
