document.addEventListener('DOMContentLoaded', function () {
    var grid = document.getElementById('category-grid');
    var hiddenSelect = document.getElementById('id_category');
    var selectedLabel = document.getElementById('category-selected-label');

    if (!grid || !hiddenSelect) return;

    var tiles = grid.querySelectorAll('.category-tile');

    // Map category names to Bootstrap Icons
    var iconMap = {
        'Noise Complaint':               'bi-volume-up-fill',
        'Garbage and Sanitation':        'bi-trash3-fill',
        'Road and Drainage Issues':      'bi-cone-striped',
        'Neighbor Dispute':              'bi-people-fill',
        'Animal Concern':                'bi-emoji-smile-fill',
        'Safety and Security':           'bi-shield-fill',
        'Street Lighting':               'bi-lightbulb-fill',
        'Illegal Parking / Obstruction': 'bi-car-front-fill',
        'Public Property Damage':        'bi-building-exclamation',
        'Others':                        'bi-three-dots',
    };

    // Apply icons from the map to each tile
    tiles.forEach(function (tile) {
        var labelEl = tile.querySelector('.category-label');
        if (!labelEl) return;
        var name = labelEl.textContent.trim();
        var iconEl = tile.querySelector('.category-icon');
        if (iconEl && iconMap[name]) {
            iconEl.className = 'bi ' + iconMap[name] + ' category-icon';
        }
    });

    // Restore selection if the page reloaded after a validation error
    if (hiddenSelect.value) {
        var preSelected = grid.querySelector('.category-tile[data-value="' + hiddenSelect.value + '"]');
        if (preSelected) {
            preSelected.classList.add('selected');
            var preName = preSelected.querySelector('.category-label').textContent.trim();
            updateLabel(preName);
        }
    }

    // Click handler
    tiles.forEach(function (tile) {
        tile.addEventListener('click', function () {
            var isAlreadySelected = this.classList.contains('selected');

            // Deselect all tiles
            tiles.forEach(function (t) { t.classList.remove('selected'); });

            if (!isAlreadySelected) {
                this.classList.add('selected');
                hiddenSelect.value = this.dataset.value;
                var name = this.querySelector('.category-label').textContent.trim();
                updateLabel(name);
            } else {
                // Clicking the same tile again deselects it
                hiddenSelect.value = '';
                updateLabel('');
            }
        });
    });

    function updateLabel(name) {
        if (!selectedLabel) return;
        if (name) {
            selectedLabel.textContent = 'Selected: ' + name;
            selectedLabel.classList.add('has-selection');
        } else {
            selectedLabel.textContent = 'No category selected';
            selectedLabel.classList.remove('has-selection');
        }
    }
});

document.addEventListener('DOMContentLoaded', function () {
    var wizard = document.getElementById('complaint-wizard');
    if (!wizard) return;

    var panels = Array.prototype.slice.call(wizard.querySelectorAll('[data-step-panel]'));
    var indicators = Array.prototype.slice.call(wizard.querySelectorAll('[data-step-target]'));
    var prevButton = wizard.querySelector('[data-wizard-prev]');
    var nextButton = wizard.querySelector('[data-wizard-next]');
    var submitButton = wizard.querySelector('[data-wizard-submit]');
    var currentStep = findFirstErrorStep();

    showStep(currentStep);

    if (prevButton) {
        prevButton.addEventListener('click', function () {
            showStep(Math.max(0, currentStep - 1));
        });
    }

    if (nextButton) {
        nextButton.addEventListener('click', function () {
            if (!validateCurrentStep()) return;
            showStep(Math.min(panels.length - 1, currentStep + 1));
        });
    }

    indicators.forEach(function (indicator) {
        indicator.addEventListener('click', function () {
            var target = Number(indicator.dataset.stepTarget);
            if (target <= currentStep || validateCurrentStep()) {
                showStep(target);
            }
        });
    });

    function showStep(index) {
        currentStep = index;
        panels.forEach(function (panel, panelIndex) {
            var isActive = panelIndex === index;
            panel.hidden = !isActive;
            panel.classList.toggle('active', isActive);
        });
        indicators.forEach(function (indicator, indicatorIndex) {
            var isActive = indicatorIndex === index;
            indicator.classList.toggle('active', isActive);
            indicator.classList.toggle('completed', indicatorIndex < index);
            if (isActive) {
                indicator.setAttribute('aria-current', 'step');
            } else {
                indicator.removeAttribute('aria-current');
            }
        });
        if (prevButton) prevButton.hidden = index === 0;
        if (nextButton) nextButton.hidden = index === panels.length - 1;
        if (submitButton) submitButton.hidden = index !== panels.length - 1;
        wizard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function validateCurrentStep() {
        var panel = panels[currentStep];
        if (!panel) return true;

        var fields = Array.prototype.slice.call(panel.querySelectorAll('input, select, textarea'));
        var firstInvalid = null;

        fields.forEach(function (field) {
            clearFieldError(field);
            if (!isFieldRequired(field) || isFilled(field)) return;
            if (!firstInvalid) firstInvalid = field;
            markFieldError(field);
        });

        if (firstInvalid) {
            focusField(firstInvalid);
            return false;
        }
        return true;
    }

    function isFieldRequired(field) {
        if (field.disabled || field.type === 'hidden') return false;
        if (field.id === 'id_category') return true;
        return field.required || field.getAttribute('aria-required') === 'true';
    }

    function isFilled(field) {
        if (field.type === 'checkbox' || field.type === 'radio') {
            var group = wizard.querySelectorAll('input[name="' + escapeSelectorValue(field.name) + '"]');
            return Array.prototype.some.call(group, function (item) { return item.checked; });
        }
        return String(field.value || '').trim().length > 0;
    }

    function focusField(field) {
        if (field.id === 'id_category') {
            var categoryGrid = document.getElementById('category-grid');
            if (categoryGrid) {
                categoryGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }
        }
        field.focus({ preventScroll: true });
        field.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function markFieldError(field) {
        field.classList.add('is-invalid');
        var wrapper = field.closest('.mb-3, .mb-4, .form-check') || field.parentElement;
        if (!wrapper || wrapper.querySelector('.wizard-field-error')) return;
        var error = document.createElement('div');
        error.className = 'text-danger small mt-1 wizard-field-error';
        error.textContent = 'Please complete this field before continuing.';
        wrapper.appendChild(error);
    }

    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        var wrapper = field.closest('.mb-3, .mb-4, .form-check') || field.parentElement;
        if (!wrapper) return;
        var existing = wrapper.querySelector('.wizard-field-error');
        if (existing) existing.remove();
    }

    function findFirstErrorStep() {
        for (var index = 0; index < panels.length; index += 1) {
            if (panels[index].querySelector('.text-danger')) {
                return index;
            }
        }
        return 0;
    }

    function escapeSelectorValue(value) {
        if (window.CSS && CSS.escape) {
            return CSS.escape(value);
        }
        return String(value).replace(/"/g, '\\"');
    }
});
