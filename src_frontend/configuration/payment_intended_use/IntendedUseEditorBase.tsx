import React, { useCallback, useEffect, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { IntendedUseType } from "../IntendedUseType.ts";
import IntendedUseEditorModal from "./IntendedUseEditorModal.tsx";

interface IntendedUseEditorBaseProps {
  intendedUseType: IntendedUseType;
  inputField: HTMLTextAreaElement;
  title: string;
}

const IntendedUseEditorBase: React.FC<IntendedUseEditorBaseProps> = ({
  intendedUseType,
  inputField,
  title,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [currentPattern, setCurrentPattern] = useState("");

  const onPatternChanged = useCallback(() => {
    setCurrentPattern(inputField.value);
  }, [inputField]);

  useEffect(() => {
    inputField.rows = 4;
    inputField.addEventListener("input", onPatternChanged);
    inputField.addEventListener("change", onPatternChanged);

    onPatternChanged();

    return () => {
      inputField.removeEventListener("input", onPatternChanged);
      inputField.removeEventListener("change", onPatternChanged);
    };
  }, [inputField, onPatternChanged]);

  useEffect(() => {
    inputField.value = currentPattern;
  }, [currentPattern]);

  return (
    <>
      <TapirButton
        icon={"edit"}
        variant={"outline-secondary"}
        onClick={() => {
          setShowModal(true);
        }}
      />
      <IntendedUseEditorModal
        show={showModal}
        onHide={() => {
          setShowModal(false);
        }}
        title={title}
        outerPattern={currentPattern}
        setOuterPattern={setCurrentPattern}
        intendedUseType={intendedUseType}
      />
    </>
  );
};

export default IntendedUseEditorBase;
