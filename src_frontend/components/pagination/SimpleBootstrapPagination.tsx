import React from "react";
import { Pagination } from "react-bootstrap";

interface SimpleBootstrapPaginationProps {
  nbPages: number;
  currentPage: number;
  goToPage: (pageIndex: number) => void;
}

const SimpleBootstrapPagination: React.FC<SimpleBootstrapPaginationProps> = ({
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

export default SimpleBootstrapPagination;
