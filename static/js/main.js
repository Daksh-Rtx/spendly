// main.js — students will add JavaScript here as features are built

/**
 * Initialise the profile-page date-filter bar.
 *
 * Presets (This Week / This Month / This Year / All Time) are plain links that
 * the server renders with the correct query-string URLs (computed in app.py).
 * The only thing JS needs to do is pre-fill the custom date inputs from the
 * current URL so a filtered view round-trips back into the form.
 */
function initDateFilterBar() {
    const form = document.querySelector('.filter-form');
    if (!form) return; // not the profile page — nothing to do

    const params = new URLSearchParams(window.location.search);
    const startInput = form.querySelector('input[name="start"]');
    const endInput = form.querySelector('input[name="end"]');

    const start = params.get('start');
    const end = params.get('end');

    // Only pre-fill when the value is a valid YYYY-MM-DD string; garbage in the
    // URL must never end up in the date inputs.
    const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

    if (startInput && start && DATE_RE.test(start)) {
        startInput.value = start;
    }
    if (endInput && end && DATE_RE.test(end)) {
        endInput.value = end;
    }
}

document.addEventListener('DOMContentLoaded', initDateFilterBar);
