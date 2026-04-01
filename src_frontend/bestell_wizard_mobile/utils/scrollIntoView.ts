import React from "react";

export function scrollIntoView(event: React.MouseEvent) {
  setTimeout(
    () => (event.target as HTMLElement)?.scrollIntoView({ behavior: "smooth" }),
    200,
  );
}
