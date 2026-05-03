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
