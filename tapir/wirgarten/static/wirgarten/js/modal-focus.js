(() => {
  const focusTargets = new WeakMap();
  let clickedControl = null;
  let clearClickedControl;

  document.addEventListener(
    "click",
    (event) => {
      clickedControl = event.target.closest("button, a, input, [tabindex]");
      clearTimeout(clearClickedControl);
      clearClickedControl = setTimeout(() => {
        clickedControl = null;
      }, 0);
    },
    true,
  );

  document.addEventListener("show.bs.modal", (event) => {
    if (!event.target.matches("#form-modal, #confirmation-modal")) return;
    if (event.defaultPrevented) return;

    focusTargets.set(
      event.target,
      event.relatedTarget || clickedControl || document.activeElement,
    );
  });

  document.addEventListener("hide.bs.modal", (event) => {
    if (event.defaultPrevented || !focusTargets.has(event.target)) return;

    // Release focus before Bootstrap marks the dialog as aria-hidden.
    if (event.target.contains(document.activeElement)) {
      document.activeElement.blur();
    }
  });

  document.addEventListener("hidden.bs.modal", (event) => {
    if (!focusTargets.has(event.target)) return;

    const trigger = focusTargets.get(event.target);
    focusTargets.delete(event.target);
    if (document.querySelector(".modal.show")) return;

    if (
      trigger instanceof HTMLElement &&
      trigger !== document.body &&
      trigger.isConnected &&
      !trigger.matches(":disabled") &&
      !trigger.closest("[inert]") &&
      trigger.getClientRects().length &&
      getComputedStyle(trigger).visibility === "visible"
    ) {
      trigger.focus({ preventScroll: true });
      if (document.activeElement === trigger) return;
    }

    document.getElementById("main-content").focus({ preventScroll: true });
  });
})();
