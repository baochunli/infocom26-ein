document.addEventListener("DOMContentLoaded", () => {
	const nav = document.querySelector("[data-nav]");
	const toggle = document.querySelector("[data-nav-toggle]");

	if (nav && toggle) {
		toggle.addEventListener("click", () => {
			const isOpen = nav.classList.toggle("is-open");
			toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
		});
	}

	const navLinks = document.querySelectorAll("[data-nav] .nav-link");
	navLinks.forEach((link) => {
		link.addEventListener("click", () => {
			if (nav && nav.classList.contains("is-open")) {
				nav.classList.remove("is-open");
				toggle && toggle.setAttribute("aria-expanded", "false");
			}
		});
	});

	// Theme toggle logic
	const themeToggle = document.querySelector(".theme-toggle");
	const html = document.documentElement;

	// Check for saved theme or system preference
	const savedTheme = localStorage.getItem("theme");
	const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
		? "dark"
		: "light";
	const initialTheme = savedTheme || systemTheme;

	html.setAttribute("data-theme", initialTheme);

	if (themeToggle) {
		themeToggle.addEventListener("click", () => {
			const currentTheme = html.getAttribute("data-theme");
			const newTheme = currentTheme === "dark" ? "light" : "dark";

			html.setAttribute("data-theme", newTheme);
			localStorage.setItem("theme", newTheme);
		});
	}
});
