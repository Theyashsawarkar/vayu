// The homepage tour: the pills above the screenshot switch it (click, or the
// arrow keys between them, the ARIA tab pattern). Nothing moves on its own.
(function () {
  const tabs = Array.from(document.querySelectorAll(".tour-tab"));
  const img = document.getElementById("tour-img");
  const caption = document.getElementById("tour-caption");
  if (!tabs.length || !img) return;

  const SHOTS = {
    "desktop": {
      alt: "The Vayu desktop: Neovim and the narada mail client tiled side by side under the glass bar, over a forest wallpaper.",
      text: "Two windows tiled, the bar above them. Every window and panel floats in its own glass.",
    },
    "panel-kendra": {
      alt: "kendra, the quick settings panel, open at the top right: Wi-Fi, Bluetooth, hotspot, do not disturb, Jyoti, phone link, dark theme, wallpaper, power and brightness.",
      text: "kendra: Wi-Fi, Bluetooth, Jyoti to keep the screen awake, the theme, power and brightness in one panel.",
    },
    "panel-dvara": {
      alt: "dvara, the app launcher, over the desktop: a list of apps on the left, the chosen app's actions on the right.",
      text: "dvara: your most-used apps first, each app's own actions, and any command if you press Shift+Enter.",
    },
    "panel-tarang": {
      alt: "tarang, the Wi-Fi panel: the connected network with live download and upload speeds, saved and nearby networks.",
      text: "tarang: networks with live signal, connect by typing the password right there, and live speeds for the one you're on.",
    },
    "panel-mudra": {
      alt: "mudra, the keybinding search: keybindings listed by what they do, with their keys as key caps.",
      text: "mudra: every keybinding on the system, found by what it does. Enter runs it.",
    },
    "notifications": {
      alt: "Two notification cards from akashvani at the top of the screen: an urgent low-battery warning outlined in red, and a calendar reminder.",
      text: "akashvani: notifications as glass cards. Red only when it's urgent.",
    },
  };

  // Fetch the others once the page has settled, so a switch is instant.
  window.addEventListener("load", () => {
    Object.keys(SHOTS).forEach((k) => { const i = new Image(); i.src = "assets/shots/" + k + ".webp"; });
  });

  function select(tab, focus) {
    const key = tab.dataset.shot;
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    if (focus) tab.focus();
    const next = "assets/shots/" + key + ".webp";
    if (img.getAttribute("src") === next) return;
    img.classList.add("swapping");
    const pre = new Image();
    pre.onload = pre.onerror = () => {
      img.src = next;
      img.alt = SHOTS[key].alt;
      if (caption) caption.textContent = SHOTS[key].text;
      requestAnimationFrame(() => img.classList.remove("swapping"));
    };
    pre.src = next;
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (e) => {
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
      else if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = tabs.length - 1;
      if (j !== null) { e.preventDefault(); select(tabs[j], true); }
    });
  });
})();
