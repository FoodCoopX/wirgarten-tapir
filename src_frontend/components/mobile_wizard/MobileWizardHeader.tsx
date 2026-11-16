import React, { ReactNode } from "react";
import "./header.css";

interface MobileWizardHeaderProps {
  logoUrl?: string;
  rightContent?: ReactNode;
}

const MobileWizardHeader: React.FC<MobileWizardHeaderProps> = ({
  logoUrl,
  rightContent,
}) => {
  return (
    <div
      id={"mobile-wizard-header"}
      style={{
        width: "100%",
        height: "100%",
      }}
      className={
        "d-flex align-items-center " +
        (rightContent ? "" : "mobile-wizard-logo-centered")
      }
    >
      {logoUrl && <img src={logoUrl} alt={"Logo"} style={{ height: "70%" }} />}
      {rightContent ?? <div />}
    </div>
  );
};

export default MobileWizardHeader;
