import React from "react";
import { Button } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface BackToWebsiteButtonProps {
  settings: BestellWizardSettings;
}

const BackToWebsiteButton: React.FC<BackToWebsiteButtonProps> = ({
  settings,
}) => {
  if (!settings.websiteUrl) {
    return null;
  }

  return (
    <div className={"d-flex justify-content-center mt-3"}>
      {/* target _top: when the wizard is embedded in an iframe, leave the iframe instead of loading the website inside it */}
      <Button
        variant={BUTTON_VARIANT}
        href={settings.websiteUrl}
        target={"_top"}
        style={{ display: "flex", alignItems: "center", gap: "6px" }}
      >
        <span className={"material-icons"}>home</span>
        <h5 className={"mb-0"}>
          {settings.strings.step14BackToWebsiteButtonText}
        </h5>
      </Button>
    </div>
  );
};

export default BackToWebsiteButton;
