function kopieerTekst(knop, tekst) {
    navigator.clipboard.writeText(tekst).then(() => {
        knop.textContent = "Gekopieerd ✓";
        knop.classList.add("gekopieerd");
        setTimeout(() => {
            knop.textContent = "Kopieer";
            knop.classList.remove("gekopieerd");
        }, 2000);
    });
}
