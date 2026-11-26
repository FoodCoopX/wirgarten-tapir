import React, { useEffect } from "react";

interface HtmlInDivProps {
  htmlContent: string;
}

const HtmlInDiv: React.FC<HtmlInDivProps> = ({ htmlContent }) => {
  useEffect(() => {
    document.getElementById("html-in-div")!.innerHTML = htmlContent;
  }, [htmlContent]);

  return (
    <div
      style={{
        border: "1px solid black",
        overflowY: "scroll",
        maxHeight: "60vh",
      }}
      id="html-in-div"
    ></div>
  );
};

export default HtmlInDiv;
