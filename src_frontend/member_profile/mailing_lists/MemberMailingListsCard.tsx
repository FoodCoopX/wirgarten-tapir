import React, { useState } from "react";
import { CoreApi } from "../../api-client";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import MailingListsCard from "./MailingListsCard.tsx";

interface MemberMailingListsCardProps {
  memberId: string;
}

const MemberMailingListsCard: React.FC<MemberMailingListsCardProps> = ({
  memberId,
}) => {
  const api = useApi(CoreApi);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function buildRequest(listName: string) {
    return {
      mailingListSubscribeInternalRecipientRequestRequest: {
        listName: listName,
        memberId: memberId,
      },
    };
  }

  return (
    <>
      <MailingListsCard
        addressLabel={"der E-Mail-Adresse aus deinem Profil"}
        loadListData={() =>
          api.coreApiMemberMailingListDataRetrieve({ memberId: memberId })
        }
        subscribe={(listName) =>
          api.coreApiMemberSelfSubscribeCreate(buildRequest(listName))
        }
        unsubscribe={(listName) =>
          api.coreApiMemberSelfUnsubscribeCreate(buildRequest(listName))
        }
        acceptInvitation={(listName) =>
          api.coreApiMemberSelfConfirmCreate(buildRequest(listName))
        }
        rejectInvitation={(listName) =>
          api.coreApiMemberSelfRejectCreate(buildRequest(listName))
        }
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MemberMailingListsCard;
