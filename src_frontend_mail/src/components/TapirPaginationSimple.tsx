import React from "react";
import { Pagination } from "react-bootstrap";

interface TapirPaginationSimpleProps {
  nbPages: number;
  currentPage: number;
  goToPage: (pageIndex: number) => void;
}

const TapirPaginationSimple: React.FC<TapirPaginationSimpleProps> = ({
  nbPages,
  currentPage,
  goToPage,
}) => {
  return (
    <>
      {Array.from({ length: nbPages }, (_, pageIndex) => (
        <Pagination.Item
          key={pageIndex}
          onClick={() => goToPage(pageIndex)}
          active={currentPage === pageIndex}
        >
          {pageIndex + 1}
        </Pagination.Item>
      ))}{" "}
    </>
  );
};

export default TapirPaginationSimple;
