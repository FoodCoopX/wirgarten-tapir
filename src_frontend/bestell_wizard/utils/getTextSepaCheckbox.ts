export function getTextSepaCheckbox(showCoopContent: boolean) {
  let string = "Ich ermächtige die Biotop Oberland eG ";
  if (showCoopContent) {
    string += "die gezeichneten Geschäftsanteile sowie ggf. ";
  }
  return (
    string +
    "die monatlichen Beträge für weitere Verträge mittels Lastschrift von meinem Bankkonto einzuziehen. Zugleich weise ich mein Kreditinstitut an, die gezogene Lastschrift einzulösen."
  );
}
