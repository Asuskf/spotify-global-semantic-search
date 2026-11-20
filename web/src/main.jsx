import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter/wght.css"; // Inter auto-hospedada (sin CDN), peso variable 100–900
import "./tokens.css";
import App from "./App.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(<App />);
