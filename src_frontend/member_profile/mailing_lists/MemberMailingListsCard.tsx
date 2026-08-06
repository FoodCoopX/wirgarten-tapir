import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Card, Form, Spinner } from "react-bootstrap";
import { CoreApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface MemberMailCategoryModalProps {
  memberId: string;
  csrfToken: string;
}

const MemberMailingListsCard: React.FC<MemberMailCategoryModalProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [allMailingLists, setAllMailingLists] = useState<string[]>([]);
  const [subscribedLists, setSubscribedLists] = useState<string[]>([]);
  const [waitingForConfirmationLists, setWaitingForConfirmationLists] =
    useState<string[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    setDataLoading(true);
    api
      .coreApiMemberMailingListDataRetrieve({ memberId: memberId })
      .then((data) => {
        setAllMailingLists(data.availableLists);
        setSubscribedLists(data.subscribedLists);
        setWaitingForConfirmationLists(data.waitingForConfirmationLists);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mailing-Listen",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }

  function onSave() {
    setSaveLoading(true);

    alert("WIP");
    return;
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
            <h5 className={"mb-0"}>Mailing-Listen</h5>
            <TapirHelpButton text={"HelpText Mailing-List Mitgliederbereich"} />
          </span>
        </Card.Header>
        <Card.Body>
          {dataLoading ? (
            <Spinner />
          ) : (
            <Form>
              {allMailingLists.map((list) => (
                <Form.Group key={list} controlId={list}>
                  <Form.Check
                    label={list}
                    checked={subscribedLists.includes(list)}
                    onChange={(event) => {
                      if (event.target.checked) {
                        setSubscribedLists([...subscribedLists, list]);
                      } else {
                        setSubscribedLists(
                          subscribedLists.filter(
                            (otherList) => otherList != list,
                          ),
                        );
                      }
                    }}
                  />
                  {waitingForConfirmationLists.includes(list) && (
                    <div>WAITING FOR CONFIRMATION</div>
                  )}
                </Form.Group>
              ))}
            </Form>
          )}
        </Card.Body>
        <Card.Footer>
          <span className={"d-flex flex-row justify-content-end"}>
            <TapirButton
              variant={"primary"}
              text={"Mailing-List Teilnahme anpassen"}
              icon={"save"}
              onClick={onSave}
              loading={saveLoading}
            />
          </span>
        </Card.Footer>
      </Card>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MemberMailingListsCard;
