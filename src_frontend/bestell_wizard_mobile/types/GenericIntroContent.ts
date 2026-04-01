export type GenericIntroContent = {
  text?: string;
  accordions?: AccordionContent[];
};

type AccordionContent = {
  title: string;
  description: string;
  order: number;
};
