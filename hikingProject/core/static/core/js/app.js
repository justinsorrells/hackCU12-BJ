document.addEventListener("DOMContentLoaded", () => {
    const navToggle = document.querySelector("[data-nav-toggle]");
    const navMenu = document.querySelector("[data-nav-menu]");

    if (!navToggle || !navMenu) {
        return;
    }

    navToggle.addEventListener("click", () => {
        const isExpanded = navToggle.getAttribute("aria-expanded") === "true";
        navToggle.setAttribute("aria-expanded", String(!isExpanded));
        navMenu.classList.toggle("is-open", !isExpanded);
        document.body.classList.toggle("nav-open", !isExpanded);
    });
});
