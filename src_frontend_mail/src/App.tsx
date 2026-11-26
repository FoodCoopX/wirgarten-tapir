import { Suspense } from "react";
import {
  Route,
  BrowserRouter as Router,
  Routes,
  useLocation,
} from "react-router-dom";
import "./App.css";
import Loading from "./components/loading";
import RouteNotFound from "./components/RouteNotFound";
import { AlertProvider } from "./contexts/alerts";
import env from "./env";
import { routes } from "./routing";

// add new routes in routing.ts

const InnerApp = () => {
  const location = useLocation();
  return (
    <Suspense
      key={location.pathname}
      fallback={
        <div style={{ width: "100%", marginTop: "5em" }}>
          <Loading />
        </div>
      }
    >
      <Routes>
        {routes.map((route, index) => (
          <Route key={index} path={route.path} element={<route.element />} />
        ))}
        <Route path="*" element={<RouteNotFound />} />
      </Routes>
    </Suspense>
  );
};

function App() {
  return (
    <div className="App" data-testid="App">
      <AlertProvider>
        <Router basename={env.REACT_APP_BASENAME}>
          <InnerApp />
        </Router>
      </AlertProvider>
    </div>
  );
}

export default App;
