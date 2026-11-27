import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import { CoreApi, type MailCategory } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import MemberExtraEmailsModal from "../personal_data/MemberExtraEmailsModal.tsx";
import MailCategoryCheckboxes from "./MailCategoryCheckboxes.tsx";

interface MemberMailCategoryModalProps {
  memberId: string;
}

const MemberMailCategoryCard: React.FC<MemberMailCategoryModalProps> = ({
  memberId,
}) => {
  const api = useApi(CoreApi);
  const [categories, setCategories] = useState<MailCategory[]>([]);
  const [categoriesRegisteredTo, setCategoriesRegisteredTo] = useState<{
    [key: string]: boolean;
  }>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    setDataLoading(true);
    api
      .coreApiMemberMailCategoryDataRetrieve({ memberId: memberId })
      .then((data) => {
        setCategories(data.categories);
        setCategoriesRegisteredTo(data.categoriesRegisteredTo);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mail-Abos",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }

  function onSave() {
    setSaveLoading(true);

    api
      .coreApiMemberMailCategoryDataCreate({
        memberMailCategoryRequestRequest: {
          memberId: memberId,
          categoriesRegisteredTo: categoriesRegisteredTo,
        },
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Mail-Abos",
          setToastDatas,
        ),
      )
      .finally(() => {
        setSaveLoading(false);
        loadData();
      });
  }

  return (
    <>
      <Card>
        <Card.Header>
          <span
            className={
              "d-flex flex-row justify-content-between align-items-center"
            }
          >
            <h5 className={"mb-0"}>Mail-Abos</h5>
          </span>
        </Card.Header>
        <Card.Body>
          {dataLoading ? (
            <Spinner />
          ) : (
            <MailCategoryCheckboxes
              categories={categories}
              categoriesRegisteredTo={categoriesRegisteredTo}
              setCategoriesRegisteredTo={setCategoriesRegisteredTo}
              alwaysOnIsLocked={true}
            />
          )}
        </Card.Body>
        <Card.Footer>
          <span className={"d-flex flex-row justify-content-end"}>
            <TapirButton
              variant={"primary"}
              text={"Speichern"}
              icon={"save"}
              onClick={onSave}
              loading={saveLoading}
            />
          </span>
        </Card.Footer>
      </Card>
      <MemberExtraEmailsModal
        memberId={memberId}
        onHide={() => setShowModal(false)}
        show={showModal}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MemberMailCategoryCard;
