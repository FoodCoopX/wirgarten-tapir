import React from "react";
import { Toast, ToastContainer } from "react-bootstrap";
import { ToastData } from "../types/ToastData.ts";

interface TapirToastContainerProps {
  toastDatas: ToastData[];
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const TapirToastContainer: React.FC<TapirToastContainerProps> = ({
  toastDatas,
  setToastDatas,
}) => {
  return (
    <ToastContainer
      position={"bottom-end"}
      containerPosition={"absolute"}
      style={{ zIndex: 2000 }}
    >
      {toastDatas.map((toastData) => (
        <Toast
          onClose={() =>
            setToastDatas(toastDatas.filter((td) => td.id !== toastData.id))
          }
          show={true}
          bg={toastData.variant}
          key={toastData.id}
          autohide={true}
        >
          <Toast.Header>{toastData.title}</Toast.Header>
          <Toast.Body>{toastData.message ?? toastData.title}</Toast.Body>
        </Toast>
      ))}
    </ToastContainer>
  );
};

export default TapirToastContainer;
