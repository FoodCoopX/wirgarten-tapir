export type GenericIntroContent = {
  title: string;
  text?: string;
  accordions?: AccordionContent[];
};

type AccordionContent = {
  title: string;
  description: string;
  order: number;
};
