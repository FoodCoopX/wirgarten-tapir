import React, { useEffect, useState } from "react";
import { Joker, JokersApi } from "../api-client";
import { useApi } from "../hooks/useApi";

declare let gettext: (english_text: string) => string;

const JokerTestCard: React.FC = () => {
  const api = useApi(JokersApi);
  const [jokers, setJokers] = useState<Joker[]>([]);

  useEffect(() => {
    api
      .jokersApiMemberJokersList({ memberId: "Hkl_XW7B9n" })
      .then(setJokers)
      .catch((error) => alert(error));
  }, []);

  return (
    <div>
      <h1>Hello from React</h1>
      <ul>
        {jokers.map((joker: Joker) => {
          return (
            <li>
              {joker.date.toString()} - {joker.member}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default JokerTestCard;
