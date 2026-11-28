import React from "react";

interface DispatchErrorMessageProps {
  errorMessage?: string | null;
}

const DispatchErrorMessage: React.FC<DispatchErrorMessageProps> = ({
  errorMessage,
}) => {
  return (
    <span>
      Beim Versand ist ein technischer Fehler aufgetreten. Details:
      <br />
      <small className="font-monospace text-muted">{errorMessage}</small>
    </span>
  );
};

export default DispatchErrorMessage;
