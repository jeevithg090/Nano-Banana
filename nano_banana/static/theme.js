// Theme handling: "system" (follow the OS), "light" or "dark".
// Loaded in <head> so the saved choice is applied before the first paint.
(() => {
    "use strict";

    const KEY = "nano-banana-theme";
    const ORDER = ["system", "light", "dark"];
    const root = document.documentElement;

    function read() {
        try {
            const value = localStorage.getItem(KEY);
            return ORDER.includes(value) ? value : "system";
        } catch {
            return "system";
        }
    }

    function apply(theme) {
        if (theme === "system") root.removeAttribute("data-theme");
        else root.setAttribute("data-theme", theme);
    }

    let current = read();
    apply(current);

    document.addEventListener("DOMContentLoaded", () => {
        const button = document.getElementById("themeToggle");
        if (!button) return;

        function sync(theme) {
            const label = `Colour theme: ${theme}`;
            button.setAttribute("aria-label", `${label}. Change theme`);
            button.title = label;
            button.dataset.theme = theme;
        }

        sync(current);
        button.addEventListener("click", () => {
            current = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];
            try {
                localStorage.setItem(KEY, current);
            } catch {
                // Storage unavailable (private mode): still switch for this page view.
            }
            apply(current);
            sync(current);
        });
    });
})();
