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
});
