export function getCsrfToken() {
  const csrf_elements = document.getElementsByName("csrfmiddlewaretoken");
  if (csrf_elements.length == 0) {
    alert("Failed to load csrf token");
    return "";
  }
  console.log("GOT " + (csrf_elements[0] as HTMLInputElement).value);
  return (csrf_elements[0] as HTMLInputElement).value;
}
