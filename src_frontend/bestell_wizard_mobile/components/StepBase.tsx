import React, { ReactNode, useEffect, useRef, useState } from "react";
import StepTitle from "./StepTitle.tsx";
import { replaceTokens } from "../utils/replaceTokens.ts";
import "./bounce.css";
import { CONTENT_HEIGHT } from "../utils/DIMENSIONS.ts";

interface StepBaseProps {
  title?: string;
  firstName: string;
  active: boolean;
  content: ReactNode;
  backgroundImageUrl: string | undefined;
}

const StepBase: React.FC<StepBaseProps> = ({
  title,
  firstName,
  active,
  content,
  backgroundImageUrl,
}) => {
  const [showScrollHint, setShowScrollHint] = useState(false);
  const scrollDiv = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !scrollDiv.current) {
      return;
    }

    scrollDiv.current.scrollTop = 0;
  }, [active]);

  useEffect(() => {
    if (!scrollDiv.current) return;

    updateScrollState();

    const resizeObserver = new ResizeObserver(() => {
      updateScrollState();
    });
    resizeObserver.observe(scrollDiv.current);

    return () => resizeObserver.disconnect();
  }, [scrollDiv]);

  function updateScrollState() {
    if (!scrollDiv.current) return;

    if (scrollDiv.current.scrollTop !== 0) {
      setShowScrollHint(false);
      return;
    }

    setShowScrollHint(
      scrollDiv.current.clientHeight + 20 < scrollDiv.current.scrollHeight,
    );
  }

  return (
    <div
      style={{
        height: CONTENT_HEIGHT + "dvh",
        width: "auto",
        overflowWrap: "anywhere",
      }}
      className={"d-flex flex-column gap-2 mx-4 test1 " + backgroundImageUrl}
    >
      {backgroundImageUrl && (
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
            backgroundImage: "url(" + backgroundImageUrl + ")",
            backgroundPosition: "center",
            backgroundSize: "cover",
            maskImage:
              "linear-gradient(0deg,rgba(255, 255, 255, 0) 0%,rgba(255, 255, 255, 1) 5%, rgba(255, 255, 255, 1) 95%, rgba(255, 255, 255, 0) 100%)",
            zIndex: -1,
            opacity: 0.2,
          }}
        />
      )}
      <div
        style={{
          height: CONTENT_HEIGHT + "dvh",
          overflowY: "scroll",
        }}
        ref={scrollDiv}
        onScroll={updateScrollState}
        className={"test2"}
      >
        <div
          className={
            "d-flex align-items-center justify-content-center gap-2 flex-column"
          }
          style={{ minHeight: CONTENT_HEIGHT + "dvh" }}
        >
          {title && <StepTitle title={replaceTokens(title, firstName)} />}
          {content}
          <span
            style={{
              position: "absolute",
              bottom: 0,
              opacity: showScrollHint ? 0.5 : 0,
              transition: "opacity 300ms",
              pointerEvents: "none",
            }}
            className={"material-icons bounce"}
          >
            arrow_cool_down
          </span>
        </div>
      </div>
    </div>
  );
};

export default StepBase;
