export function getPeriodId() {
  const urlParameters = Object.fromEntries(
    window.location.search
      .substring(1)
      .split("&")
      .map((kv) => kv.split("=")),
  );
  return urlParameters["periodId"];
}
