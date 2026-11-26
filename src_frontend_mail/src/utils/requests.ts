import { getCookie } from "./cookies";

export function addCsrfToken(formData: FormData) {
  const csrfToken = getCookie("csrftoken");
  formData.append("csrfmiddlewaretoken", csrfToken);
  return formData;
}
