import { useEffect } from "react";

// Asks for confirmation before leaving the page, e.g. while editing an email.
export function usePreventUnload() {
  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);
}
