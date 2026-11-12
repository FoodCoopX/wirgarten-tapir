import React from "react";

export function onEnterOrSpace(handler: () => void) {
  return (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handler();
    }
  };
}
