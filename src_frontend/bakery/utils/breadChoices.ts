// Texts about members' bread choices that switching a bread off or copying a
// week clears.

export const choicesText = (count: number) =>
  `${count} ${count === 1 ? "Brotwahl" : "Brotwahlen"}`;

// "wird"/"werden" and the like, by the number of choices.
export const byCount = (count: number, singular: string, plural: string) =>
  count === 1 ? singular : plural;
