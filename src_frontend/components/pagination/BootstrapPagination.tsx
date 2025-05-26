import React from "react";
import { Pagination } from "react-bootstrap";
import SimpleBootstrapPagination from "./SimpleBootstrapPagination";
import ComplexBootstrapPagination from "./ComplexBootstrapPagination";

interface BootstrapPaginationProps {
  pageSize: number;
  itemCount: number;
  currentPage: number;
  goToPage: (pageIndex: number) => void;
}

const BootstrapPagination: React.FC<BootstrapPaginationProps> = ({
  pageSize,
  itemCount,
  currentPage,
  goToPage,
}) => {
  const nbPages = Math.ceil(itemCount / pageSize);
  return (
    <Pagination className="mb-0">
      {nbPages > 9 ? (
        <ComplexBootstrapPagination
          nbPages={nbPages}
          currentPage={currentPage}
          goToPage={goToPage}
        />
      ) : (
        <SimpleBootstrapPagination
          nbPages={nbPages}
          currentPage={currentPage}
          goToPage={goToPage}
        />
      )}
    </Pagination>
  );
};

export default BootstrapPagination;
