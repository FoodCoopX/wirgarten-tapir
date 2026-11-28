import React, { useEffect, useRef, useState } from "react";
import { Alert, Badge, Form } from "react-bootstrap";

const SPLIT_CHARS = [",", ";", " "];

interface EmailInputProps {
  onEmailListChange: (emails: string[]) => void;
  initialValue?: string[];
  autoFocus?: boolean;
}

const EmailInput: React.FC<EmailInputProps> = ({
  onEmailListChange,
  initialValue = [],
  autoFocus = true,
}) => {
  const [inputValue, setInputValue] = useState<string>("");
  const [emailList, setEmailList] = useState<string[]>([]);
  const [isValidEmail, setIsValidEmail] = useState<boolean>(true);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus, inputRef]);

  useEffect(() => {
    if (initialValue.length > 0) {
      console.log(initialValue);
      setEmailList(initialValue);
    }
  }, [initialValue]);

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
    const newEmails = [...emailList];
    emails.forEach((email) => {
      const trimmedEmail = email.trim();
      if (validateEmail(trimmedEmail) && !newEmails.includes(trimmedEmail)) {
        newEmails.push(trimmedEmail);
      }
    });
    setEmailList(newEmails);
    onEmailListChange(newEmails);
  };

  const addEmail = (email: string) => {
    if (email) {
      if (validateEmail(email)) {
        setIsValidEmail(true);
        if (!emailList.includes(email)) {
          const newEmailList = [...emailList, email];
          onEmailListChange(newEmailList);
          setEmailList(newEmailList);
        }
        setInputValue("");
      } else {
        setIsValidEmail(false);
        setInputValue(email);
      }
    }
  };

  const removeEmail = (email: string) => {
    const newEmailList = emailList.filter((e) => e !== email);
    setEmailList(newEmailList);
    onEmailListChange(newEmailList);
  };

  const handleBlur = () => {
    addEmail(inputValue.trim());
  };

  return (
    <div>
      {!isValidEmail && <Alert variant="warning">Invalid email address</Alert>}
      {emailList.map((email, index) => (
        <Badge
          title="Click to remove"
          style={{
            cursor: "pointer",
            marginRight: "0.5em",
            marginBottom: "0.5em",
          }}
          key={index}
          className="mr-2"
          onClick={() => removeEmail(email)}
        >
          {email}
        </Badge>
      ))}
      <Form>
        <Form.Control
          style={{ marginTop: "1em" }}
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
      </Form>
    </div>
  );
};

export default EmailInput;
