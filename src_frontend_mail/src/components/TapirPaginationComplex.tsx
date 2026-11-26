import React from "react";
import { Pagination } from "react-bootstrap";

interface TapirPaginationComplexProps {
  nbPages: number;
  currentPage: number;
  goToPage: (pageIndex: number) => void;
}

const TapirPaginationComplex: React.FC<TapirPaginationComplexProps> = ({
  nbPages,
  currentPage,
  goToPage,
}) => {
  function itemIsVisible(pageIndex: number) {
    const distanceToCurrent = Math.abs(pageIndex - currentPage);
    return distanceToCurrent <= 2;
  }

  return (
    <>
      <Pagination.First
        onClick={() => goToPage(0)}
        disabled={currentPage == 0}
      />
      <Pagination.Prev
        onClick={() => goToPage(currentPage - 1)}
        disabled={currentPage == 0}
      />
      {currentPage > 2 && <Pagination.Ellipsis disabled={true} />}
      {Array.from(
        { length: nbPages },
        (_, pageIndex) =>
          itemIsVisible(pageIndex) && (
            <Pagination.Item
              key={pageIndex}
              onClick={() => goToPage(pageIndex)}
              active={currentPage === pageIndex}
            >
              {pageIndex + 1}
            </Pagination.Item>
          ),
      )}
      {nbPages - currentPage > 3 && <Pagination.Ellipsis disabled={true} />}
      <Pagination.Next
        onClick={() => goToPage(currentPage + 1)}
        disabled={currentPage == nbPages - 1}
      />
      <Pagination.Last
        onClick={() => goToPage(nbPages - 1)}
        disabled={currentPage == nbPages - 1}
      />
    </>
  );
};

export default TapirPaginationComplex;
