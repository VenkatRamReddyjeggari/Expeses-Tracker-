// main.js — students will add JavaScript here as features are built

// Ask before submitting any form marked with data-confirm (e.g. deleting an expense).
document.addEventListener("submit", function (event) {
    const message = event.target.dataset.confirm;
    if (message && !window.confirm(message)) {
        event.preventDefault();
    }
});
