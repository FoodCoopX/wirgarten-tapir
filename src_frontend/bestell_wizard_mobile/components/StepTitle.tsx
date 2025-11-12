import React from "react";

interface StepTitleProps {
  title: string;
}

const StepTitle: React.FC<StepTitleProps> = ({ title }) => {
  return <h3 className={"text-center"}>{title}</h3>;
};

export default StepTitle;
