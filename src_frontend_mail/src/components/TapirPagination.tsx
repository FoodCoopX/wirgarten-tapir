import React from "react";
import { Pagination } from "react-bootstrap";
import TapirPaginationComplex from "./TapirPaginationComplex";
import TapirPaginationSimple from "./TapirPaginationSimple";

interface TapirPaginationProps {
  pageSize: number;
  itemCount: number;
  currentPage: number;
  goToPage: (pageIndex: number) => void;
}

const TapirPagination: React.FC<TapirPaginationProps> = ({
  pageSize,
  itemCount,
  currentPage,
  goToPage,
}) => {
  const nbPages = Math.ceil(itemCount / pageSize);

  return (
    <Pagination className="mb-0">
      {nbPages > 9 ? (
        <TapirPaginationComplex
          nbPages={nbPages}
          currentPage={currentPage}
          goToPage={goToPage}
        />
      ) : (
        <TapirPaginationSimple
          nbPages={nbPages}
          currentPage={currentPage}
          goToPage={goToPage}
        />
      )}
    </Pagination>
  );
};

export default TapirPagination;
