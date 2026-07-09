import "./theme/tokens.css";
import "./theme/fonts.css";
import "./theme/crt.css";
import { BootSequence } from "./boot/BootSequence";
import { Desktop } from "./os/Desktop";

document.body.insertAdjacentHTML("afterbegin", '<div class="crt-overlay"></div>');

new BootSequence(() => {
  const root = document.getElementById("os-root");
  if (!root) return;
  new Desktop(root);
}).start();
