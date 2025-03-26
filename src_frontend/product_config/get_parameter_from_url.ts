export function getPeriodIdFromUrl() {
  return getParameterFromUrl("periodId");
}

export function getProductIdFromUrl() {
  return getParameterFromUrl("prodId");
}

function getParameterFromUrl(parameter: string) {
  const urlParameters = Object.fromEntries(
    window.location.search
      .substring(1)
      .split("&")
      .map((kv) => kv.split("=")),
  );
  return urlParameters[parameter];
}
