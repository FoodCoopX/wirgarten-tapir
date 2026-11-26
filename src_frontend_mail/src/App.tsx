import { AnimatePresence, motion } from "framer-motion";
import { Suspense, useEffect } from "react";
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
  useEffect(() => {
    const setCookie = (name: string, value: string) => {
      document.cookie = name + "=" + value + "; Path=/; SameSite=Lax;";
    };

    const handleMessage = (event: MessageEvent) => {
      if (!env.REACT_APP_API_ROOT.startsWith(event.origin)) {
        console.log("Ignoring message from unknown origin", event.origin);
        return;
      }

      if (event.data.type === "NEW_TOKEN") {
        const newToken = event.data.token;
        setCookie("token", newToken);
      }
    };

    window.addEventListener("message", handleMessage);

    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const location = useLocation();
  return (
    <motion.div
      key={location.pathname}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <Suspense
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
    </motion.div>
  );
};

function App() {
  return (
    <div className="App" data-testid="App">
      <AlertProvider>
        <AnimatePresence mode="wait">
          <Router basename={env.REACT_APP_BASENAME}>
            <InnerApp />
          </Router>
        </AnimatePresence>
      </AlertProvider>
    </div>
  );
}

export default App;
