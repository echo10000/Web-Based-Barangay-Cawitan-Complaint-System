document.addEventListener('DOMContentLoaded', function () {
    var pw1 = document.getElementById('id_password1');
    var pw2 = document.getElementById('id_password2');

    if (!pw1) return;

    // Update a requirement item's visual state
    function setReq(el, met, active) {
        if (!el) return;
        var icon = el.querySelector('i');
        el.classList.remove('req-met', 'req-fail');

        if (!active) {
            // User hasn't typed yet — show neutral circle
            if (icon) icon.className = 'bi bi-circle';
            return;
        }

        if (met) {
            el.classList.add('req-met');
            if (icon) icon.className = 'bi bi-check-circle-fill';
        } else {
            el.classList.add('req-fail');
            if (icon) icon.className = 'bi bi-x-circle-fill';
        }
    }

    function checkPassword() {
        var val = pw1.value;
        var active = val.length > 0;

        // Requirement 1: at least 8 characters
        setReq(
            document.getElementById('req-length'),
            val.length >= 8,
            active
        );

        // Requirement 2: not entirely numeric
        setReq(
            document.getElementById('req-numeric'),
            !/^\d+$/.test(val),
            active
        );

        // Also refresh the match check whenever password 1 changes
        checkMatch();
    }

    function checkMatch() {
        if (!pw2) return;
        var val1 = pw1.value;
        var val2 = pw2.value;
        var active = val2.length > 0;

        setReq(
            document.getElementById('req-match'),
            val1 === val2 && val1.length > 0,
            active
        );
    }

    pw1.addEventListener('input', checkPassword);
    if (pw2) pw2.addEventListener('input', checkMatch);
});
