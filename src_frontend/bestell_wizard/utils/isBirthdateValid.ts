import dayjs from "dayjs";

export function isBirthdateValid(birthdate: Date): boolean {
  const today = dayjs();
  const age = today.diff(birthdate, "years");
  return age >= 18 && age < 150;
}
