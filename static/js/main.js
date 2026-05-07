document.addEventListener("DOMContentLoaded", () => {
    const topNavbar = document.querySelector("#topNavbar");
    const topNavbarToggle = document.querySelector(".app-navbar .navbar-toggler");

    if (topNavbar && topNavbarToggle) {
        topNavbarToggle.addEventListener("click", () => {
            const wasExpanded = topNavbarToggle.getAttribute("aria-expanded") === "true";
            window.setTimeout(() => {
                const bootstrapHandled = topNavbarToggle.getAttribute("aria-expanded") !== String(wasExpanded);
                if (bootstrapHandled) return;
                const shouldOpen = !topNavbar.classList.contains("show");
                topNavbar.classList.toggle("show", shouldOpen);
                topNavbarToggle.setAttribute("aria-expanded", String(shouldOpen));
            }, 0);
        });
    }

    const sidebar = document.querySelector(".app-sidebar");
    const sidebarToggle = document.querySelector("[data-sidebar-toggle]");
    const sidebarCloseTargets = document.querySelectorAll("[data-sidebar-close]");
    const sidebarLinks = document.querySelectorAll(".app-sidebar a.sidebar-link");
    const mobileSidebarQuery = window.matchMedia("(max-width: 900px)");

    const setSidebarOpen = (isOpen) => {
        if (!sidebar || !sidebarToggle) return;
        document.body.classList.toggle("sidebar-open", isOpen);
        sidebarToggle.setAttribute("aria-expanded", String(isOpen));
        sidebarToggle.setAttribute("aria-label", isOpen ? "Close sidebar menu" : "Open sidebar menu");
    };

    if (sidebar && sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
            setSidebarOpen(!document.body.classList.contains("sidebar-open"));
        });

        sidebarCloseTargets.forEach((target) => {
            target.addEventListener("click", () => setSidebarOpen(false));
        });

        sidebarLinks.forEach((link) => {
            link.addEventListener("click", () => {
                if (mobileSidebarQuery.matches) setSidebarOpen(false);
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") setSidebarOpen(false);
        });

        mobileSidebarQuery.addEventListener("change", (event) => {
            if (!event.matches) setSidebarOpen(false);
        });
    }

    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            const instance = bootstrap.Alert.getOrCreateInstance(alert);
            instance.close();
        }, 4500);
    });

    const statusForms = document.querySelectorAll("[data-account-status-confirm]");
    if (statusForms.length) {
        const modalElement = document.createElement("div");
        modalElement.className = "modal fade account-status-modal";
        modalElement.id = "accountStatusConfirmModal";
        modalElement.tabIndex = -1;
        modalElement.setAttribute("aria-labelledby", "accountStatusConfirmTitle");
        modalElement.setAttribute("aria-hidden", "true");
        modalElement.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content account-status-modal-card">
                    <div class="modal-body">
                        <div class="account-status-modal-icon" data-account-status-icon>
                            <i class="bi bi-person-lock"></i>
                        </div>
                        <h2 id="accountStatusConfirmTitle" class="account-status-modal-title">Update account access?</h2>
                        <p class="account-status-modal-copy" data-account-status-copy></p>
                        <div class="account-status-modal-actions">
                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn account-status-confirm-button" data-account-status-confirm-button>Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalElement);

        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        const title = modalElement.querySelector("#accountStatusConfirmTitle");
        const copy = modalElement.querySelector("[data-account-status-copy]");
        const icon = modalElement.querySelector("[data-account-status-icon]");
        const confirmButton = modalElement.querySelector("[data-account-status-confirm-button]");
        let pendingForm = null;

        statusForms.forEach((form) => {
            form.addEventListener("submit", (event) => {
                if (form.dataset.accountStatusConfirmed === "true") return;
                event.preventDefault();
                pendingForm = form;
                const action = form.dataset.accountAction || "update";
                const accountName = form.dataset.accountName || "this account";
                const isDeactivate = action === "deactivate";
                title.textContent = isDeactivate ? "Deactivate account access?" : "Activate account access?";
                copy.textContent = isDeactivate
                    ? `${accountName} will not be able to log in until the account is activated again.`
                    : `${accountName} will be able to log in again after activation.`;
                icon.classList.toggle("is-danger", isDeactivate);
                icon.classList.toggle("is-success", !isDeactivate);
                confirmButton.classList.toggle("btn-danger", isDeactivate);
                confirmButton.classList.toggle("btn-success", !isDeactivate);
                confirmButton.textContent = isDeactivate ? "Deactivate Account" : "Activate Account";
                modal.show();
            });
        });

        confirmButton.addEventListener("click", () => {
            if (!pendingForm) return;
            pendingForm.dataset.accountStatusConfirmed = "true";
            modal.hide();
            pendingForm.submit();
        });
    }

    const ratingLabels = {
        1: "Poor",
        2: "Fair",
        3: "Good",
        4: "Very Good",
        5: "Excellent",
    };

    document.querySelectorAll("[data-feedback-component]").forEach((component) => {
        const form = component.querySelector("[data-feedback-form]");
        const ratingInput = component.querySelector("[data-feedback-rating-input]");
        const acceptanceInput = component.querySelector("[data-feedback-acceptance-input]");
        const stars = Array.from(component.querySelectorAll("[data-feedback-star]"));
        const ratingLabel = component.querySelector("[data-feedback-rating-label]");
        const toggles = Array.from(component.querySelectorAll("[data-feedback-acceptance]"));
        const textarea = component.querySelector("[data-feedback-comments]");
        const counter = component.querySelector("[data-feedback-counter]");
        const submit = component.querySelector("[data-feedback-submit]");
        const success = component.querySelector("[data-feedback-success]");
        const maxTextareaHeight = 154;
        let selectedRating = Number(ratingInput?.value || 0);
        let selectedAcceptance = acceptanceInput?.value || "";

        const paintStars = (score, preview = false) => {
            stars.forEach((star) => {
                const value = Number(star.dataset.feedbackStar);
                const isFilled = value <= score;
                star.textContent = isFilled ? "★" : "☆";
                star.classList.toggle("is-preview", preview && isFilled);
                star.classList.toggle("is-active", !preview && value <= selectedRating);
                star.setAttribute("aria-checked", String(value === selectedRating));
            });
        };

        const updateSubmitState = () => {
            if (!submit) return;
            const isReady = Boolean(selectedRating && selectedAcceptance);
            submit.classList.toggle("is-disabled", !isReady);
            submit.setAttribute("aria-disabled", String(!isReady));
        };

        const setRating = (score) => {
            selectedRating = score;
            if (ratingInput) ratingInput.value = String(score);
            if (ratingLabel) ratingLabel.textContent = ratingLabels[score] || "Select a rating";
            paintStars(score);
            updateSubmitState();
        };

        const previewRating = (score) => {
            paintStars(score, true);
            if (ratingLabel) ratingLabel.textContent = ratingLabels[score] || "Select a rating";
        };

        const restoreRating = () => {
            paintStars(selectedRating);
            if (ratingLabel) ratingLabel.textContent = ratingLabels[selectedRating] || "Select a rating";
        };

        const setAcceptance = (value) => {
            selectedAcceptance = value;
            if (acceptanceInput) acceptanceInput.value = value;
            toggles.forEach((toggle) => {
                const isActive = toggle.dataset.feedbackAcceptance === value;
                toggle.classList.toggle("is-active", isActive);
                toggle.setAttribute("aria-pressed", String(isActive));
            });
            updateSubmitState();
        };

        const updateTextarea = () => {
            if (!textarea) return;
            textarea.style.height = "auto";
            textarea.style.height = `${Math.min(textarea.scrollHeight, maxTextareaHeight)}px`;
            if (counter) counter.textContent = `${textarea.value.length} / 300`;
        };

        const shake = () => {
            component.classList.remove("is-shaking");
            void component.offsetWidth;
            component.classList.add("is-shaking");
        };

        stars.forEach((star) => {
            const score = Number(star.dataset.feedbackStar);
            star.addEventListener("mouseenter", () => previewRating(score));
            star.addEventListener("focus", () => previewRating(score));
            star.addEventListener("mouseleave", restoreRating);
            star.addEventListener("blur", restoreRating);
            star.addEventListener("click", () => setRating(score));
        });

        toggles.forEach((toggle) => {
            toggle.setAttribute("aria-pressed", "false");
            toggle.addEventListener("click", () => setAcceptance(toggle.dataset.feedbackAcceptance));
        });

        textarea?.addEventListener("input", updateTextarea);

        form?.addEventListener("submit", (event) => {
            if (!selectedRating || !selectedAcceptance) {
                event.preventDefault();
                shake();
                return;
            }
            if (submit) {
                submit.disabled = true;
                submit.textContent = "\u2713 Submit Feedback";
            }
            if (success) {
                success.hidden = false;
            }
        });

        if (selectedRating) setRating(selectedRating);
        if (selectedAcceptance) setAcceptance(selectedAcceptance);
        paintStars(selectedRating);
        updateTextarea();
        updateSubmitState();
    });
});
