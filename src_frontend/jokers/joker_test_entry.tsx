import { createRoot } from "react-dom/client";
import JokerTestCard from "./JokerTestCard.tsx";

const domNode = document.getElementById("joker_test");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<JokerTestCard />);
} else {
  console.error("Failed to render home test from React");
}
