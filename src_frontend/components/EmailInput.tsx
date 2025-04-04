import React, { useEffect, useRef, useState } from "react";
import { Alert, Badge, Form } from "react-bootstrap";

const SPLIT_CHARS = [",", ";", " "];

interface EmailInputProps {
  onEmailListChange: (emails: string[]) => void;
  addresses: string[];
  autoFocus?: boolean;
}

const EmailInput: React.FC<EmailInputProps> = ({
  onEmailListChange,
  addresses,
  autoFocus = true,
}) => {
  const [inputValue, setInputValue] = useState<string>("");
  const [isValidEmail, setIsValidEmail] = useState<boolean>(true);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus, inputRef]);

  const validateEmail = (email: string) => {
    const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return re.test(String(email).toLowerCase());
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value.toLowerCase().trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ([...SPLIT_CHARS, "Enter"].includes(e.key)) {
      e.preventDefault();
      addEmail(inputValue.trim());
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text");
    const emails = pastedData.split(/[ ,;]+/);
    const newEmails = [...addresses];
    emails.forEach((email) => {
      const trimmedEmail = email.trim();
      if (validateEmail(trimmedEmail) && !newEmails.includes(trimmedEmail)) {
        newEmails.push(trimmedEmail);
      }
    });
    onEmailListChange(newEmails);
  };

  const addEmail = (email: string) => {
    if (!email) {
      return;
    }

    if (validateEmail(email)) {
      setIsValidEmail(true);
      if (!addresses.includes(email)) {
        onEmailListChange([...addresses, email]);
      }
      setInputValue("");
    } else {
      setIsValidEmail(false);
      setInputValue(email);
    }
  };

  const removeEmail = (email: string) => {
    onEmailListChange(addresses.filter((e) => e !== email));
  };

  const handleBlur = () => {
    addEmail(inputValue.trim());
  };

  return (
    <div className={"d-flex flex-column"}>
      {!isValidEmail && <Alert variant="warning">Invalid email address</Alert>}
      {addresses.length > 0 && (
        <div className={"d-flex flex-row gap-2 mb-2"}>
          {addresses.map((address, index) => (
            <Badge
              title="Click to remove"
              style={{
                cursor: "pointer",
              }}
              key={index}
              onClick={() => removeEmail(address)}
            >
              {address}
            </Badge>
          ))}
        </div>
      )}
      <Form.Control
        as="input"
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        ref={inputRef}
        placeholder="Empfänger hinzufügen"
        onBlur={handleBlur}
      />
    </div>
  );
};

export default EmailInput;
