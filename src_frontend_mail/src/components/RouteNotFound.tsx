import React from "react";
import { routes } from "../routing";

interface RouteNotFoundProps {}

const RouteNotFound: React.FC<RouteNotFoundProps> = ({}) => {
  return (
    <>
      <div
        style={{
          display: "flex",
          gap: "10px",
          justifyContent: "center",
          marginTop: "20px",
          flexDirection: "column",
        }}
      >
        <div>ROUTE NOT FOUND</div>
        <ul>
          {routes.map((route) => (
            <li key={route.path}>{route.path}</li>
          ))}
        </ul>
      </div>
    </>
  );
};

export default RouteNotFound;
