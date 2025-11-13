import React, { ReactNode, useEffect, useRef, useState } from "react";
import StepTitle from "./StepTitle.tsx";
import { replaceTokens } from "../utils/replaceTokens.ts";
import "./bounce.css";

interface StepBaseProps {
  title?: string;
  firstName: string;
  active: boolean;
  content: ReactNode;
}

const StepBase: React.FC<StepBaseProps> = ({
  title,
  firstName,
  active,
  content,
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
      scrollDiv.current.clientHeight < scrollDiv.current.scrollHeight,
    );
  }

  return (
    <div
      style={{
        height: "80dvh",
        width: "auto",
      }}
      className={"d-flex flex-column gap-2 mx-4"}
    >
      <div
        style={{
          height: "80dvh",
          overflowY: "scroll",
        }}
        ref={scrollDiv}
        onScroll={updateScrollState}
      >
        <div
          className={
            "d-flex align-items-center justify-content-center gap-2 flex-column"
          }
          style={{ minHeight: "80dvh" }}
        >
          {title && <StepTitle title={replaceTokens(title, firstName)} />}
          {content}
          <span
            style={{
              position: "absolute",
              bottom: 0,
              opacity: showScrollHint ? 0.5 : 0,
              transition: "opacity 300ms",
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
