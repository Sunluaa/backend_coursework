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

        document.querySelectorAll("[data-question-form]").forEach((questionForm) => {
            const questionTypeSelect = questionForm.querySelector('select[name="question_type"]');
            const ratingScaleField = questionForm.querySelector("[data-rating-scale-field]");
            const choiceBuilder = questionForm.querySelector("[data-choice-builder]");
            const choiceList = questionForm.querySelector("[data-choice-list]");
            const choiceTemplate = questionForm.querySelector("[data-choice-template]");
            const choiceAddButton = questionForm.querySelector("[data-choice-add]");
            const maxChoices = Number(choiceBuilder?.dataset.maxChoices || 11);

            const syncRatingScaleField = () => {
                if (!questionTypeSelect || !ratingScaleField) {
                    return;
                }
                ratingScaleField.hidden = questionTypeSelect.value !== "rating";
            };

            const updateChoiceState = () => {
                if (!choiceBuilder || !choiceAddButton || !choiceList) {
                    return;
                }

                const isChoiceType = questionTypeSelect
                    && (questionTypeSelect.value === "single_choice" || questionTypeSelect.value === "multiple_choice");
                choiceBuilder.hidden = !isChoiceType;
                choiceAddButton.disabled = !isChoiceType || choiceList.children.length >= maxChoices;
                choiceAddButton.hidden = !isChoiceType;
            };

            const appendChoiceRow = (value = "") => {
                if (!choiceList || !choiceTemplate) {
                    return;
                }
                if (choiceList.children.length >= maxChoices) {
                    return;
                }

                const fragment = choiceTemplate.content.cloneNode(true);
                const row = fragment.querySelector(".choice-row");
                const input = fragment.querySelector('input[name="choice_texts"]');

                if (input) {
                    input.value = value;
                }

                if (row) {
                    choiceList.appendChild(row);
                } else {
                    choiceList.appendChild(fragment);
                }

                updateChoiceState();
            };

            if (questionTypeSelect) {
                syncRatingScaleField();
                updateChoiceState();
                questionTypeSelect.addEventListener("change", () => {
                    syncRatingScaleField();
                    updateChoiceState();
                });
            }

            if (choiceAddButton) {
                choiceAddButton.addEventListener("click", () => appendChoiceRow());
            }

            if (choiceList) {
                choiceList.addEventListener("click", (event) => {
                    const removeButton = event.target.closest("[data-choice-remove]");
                    if (!removeButton) {
                        return;
                    }
                    const row = removeButton.closest(".choice-row");
                    if (row) {
                        row.remove();
                    }
                    if (choiceList.children.length === 0) {
                        appendChoiceRow();
                    }
                    updateChoiceState();
                });
            }
        });

        const csrfToken = () => {
            const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) {
                return csrfInput.value;
            }

            const cookie = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
            return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
        };

        document.querySelectorAll("[data-question-list]").forEach((questionList) => {
            let draggedItem = null;

            const questionItems = () => Array.from(questionList.querySelectorAll("[data-question-item]"));

            const itemAfterPointer = (clientY) => {
                return questionItems()
                    .filter((item) => item !== draggedItem)
                    .reduce(
                        (closest, item) => {
                            const box = item.getBoundingClientRect();
                            const offset = clientY - box.top - box.height / 2;
                            if (offset < 0 && offset > closest.offset) {
                                return { offset, item };
                            }
                            return closest;
                        },
                        { offset: Number.NEGATIVE_INFINITY, item: null }
                    ).item;
            };

            const persistQuestionOrder = () => {
                const reorderUrl = questionList.dataset.reorderUrl;
                if (!reorderUrl) {
                    return;
                }

                const formData = new FormData();
                questionItems().forEach((item) => {
                    formData.append("question_ids", item.dataset.questionId);
                });

                fetch(reorderUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: formData,
                }).then((response) => {
                    if (!response.ok) {
                        window.location.reload();
                    }
                }).catch(() => window.location.reload());
            };

            questionList.addEventListener("dragstart", (event) => {
                const handle = event.target.closest("[data-drag-handle]");
                if (!handle) {
                    return;
                }

                draggedItem = handle.closest("[data-question-item]");
                if (!draggedItem) {
                    return;
                }

                draggedItem.classList.add("is-dragging");
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", draggedItem.dataset.questionId);
            });

            questionList.addEventListener("dragover", (event) => {
                if (!draggedItem) {
                    return;
                }

                event.preventDefault();
                const nextItem = itemAfterPointer(event.clientY);
                if (nextItem) {
                    questionList.insertBefore(draggedItem, nextItem);
                } else {
                    questionList.appendChild(draggedItem);
                }
            });

            questionList.addEventListener("dragend", () => {
                if (!draggedItem) {
                    return;
                }

                draggedItem.classList.remove("is-dragging");
                draggedItem = null;
                persistQuestionOrder();
            });
        });

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
