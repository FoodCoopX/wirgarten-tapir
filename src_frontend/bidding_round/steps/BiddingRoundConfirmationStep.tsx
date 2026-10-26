import React from "react";
import { Button } from "react-bootstrap";

import { getBiddingRoundLoginUrl } from "../utils/getBiddingRoundLoginUrl.ts";

interface BiddingRoundConfirmationStepProps {
  contentHtml: string;
  showLoginButton: boolean;
}

const BiddingRoundConfirmationStep: React.FC<
  BiddingRoundConfirmationStepProps
> = ({ contentHtml, showLoginButton }) => {
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
      {showLoginButton && (
        <Button href={getBiddingRoundLoginUrl()} variant={"dark"}>
          {"Anmelden"}
        </Button>
      )}
    </div>
  );
};

export default BiddingRoundConfirmationStep;
