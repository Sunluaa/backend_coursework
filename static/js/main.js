(() => {
    const storageKey = "oprosnik-theme";
    const root = document.documentElement;

    const getTheme = () => root.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";

    const saveTheme = (theme) => {
        root.setAttribute("data-bs-theme", theme);
        try {
            localStorage.setItem(storageKey, theme);
        } catch (error) {
            // Theme switching still works for the current page if storage is unavailable.
        }
    };

    const updateThemeToggle = (toggle) => {
        const isDark = getTheme() === "dark";
        toggle.setAttribute("aria-pressed", String(isDark));
        toggle.setAttribute("title", isDark ? "Включить светлую тему" : "Включить темную тему");
        toggle.setAttribute("aria-label", isDark ? "Включить светлую тему" : "Включить темную тему");
    };

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".alert").forEach((alert) => {
            setTimeout(() => {
                if (window.bootstrap) {
                    bootstrap.Alert.getOrCreateInstance(alert).close();
                }
            }, 7000);
        });

        const themeToggle = document.getElementById("themeToggle");
        if (themeToggle) {
            updateThemeToggle(themeToggle);
            themeToggle.addEventListener("click", () => {
                saveTheme(getTheme() === "dark" ? "light" : "dark");
                updateThemeToggle(themeToggle);
            });
        }

        const questionTypeSelect = document.querySelector('select[name="question_type"]');
        const ratingScaleField = document.querySelector("[data-rating-scale-field]");
        if (questionTypeSelect && ratingScaleField) {
            const syncRatingScaleField = () => {
                ratingScaleField.hidden = questionTypeSelect.value !== "rating";
            };
            syncRatingScaleField();
            questionTypeSelect.addEventListener("change", syncRatingScaleField);
        }

        document.querySelectorAll(".rating-range-input").forEach((input) => {
            const range = input.closest(".rating-range");
            const output = range ? range.querySelector("[data-rating-value]") : null;

            const syncRange = () => {
                const min = Number(input.min || 1);
                const max = Number(input.max || 5);
                const value = Number(input.value || min);
                const progress = max > min ? ((value - min) / (max - min)) * 100 : 0;

                input.style.setProperty("--range-progress", `${progress}%`);
                if (output) {
                    output.value = String(value);
                    output.textContent = String(value);
                }
            };

            syncRange();
            input.addEventListener("input", syncRange);
            input.addEventListener("change", syncRange);
        });
    });
})();
