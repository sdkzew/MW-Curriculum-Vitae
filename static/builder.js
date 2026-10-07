const form = document.querySelector("#cv-builder");
const preview = document.querySelector("#cv-preview");

function textOrFallback(id, fallback) {
    const field = document.querySelector(`#${id}`);
    return field && field.value.trim() ? field.value.trim() : fallback;
}

function updatePreview() {
    document.querySelector("#preview-name").textContent = textOrFallback("full_name", "NUMELE TĂU");
    document.querySelector("#preview-headline").textContent = textOrFallback("headline", "Titlul profesional");
    document.querySelector("#preview-summary").textContent = textOrFallback(
        "summary",
        "Un rezumat profesional concis va apărea aici."
    );
    const email = textOrFallback("email", "email");
    const location = textOrFallback("location", "locație");
    document.querySelector("#preview-contact").textContent = `${email} · ${location}`;
}

function renumberRows(list, label) {
    list.querySelectorAll(".repeatable-item").forEach((item, index) => {
        item.querySelector(".repeatable-head strong").textContent = `${label} ${String(index + 1).padStart(2, "0")}`;
    });
}

function addRow(listId, templateId, label) {
    const list = document.querySelector(`#${listId}`);
    if (list.children.length >= 8) return;
    const template = document.querySelector(`#${templateId}`);
    list.append(template.content.cloneNode(true));
    renumberRows(list, label);
}

document.querySelector("#add-experience").addEventListener("click", () => {
    addRow("experience-list", "experience-template", "EXPERIENȚĂ");
});

document.querySelector("#add-education").addEventListener("click", () => {
    addRow("education-list", "education-template", "EDUCAȚIE");
});

form.addEventListener("click", (event) => {
    const button = event.target.closest(".remove-row");
    if (!button) return;
    const list = button.closest(".repeatable-list");
    const label = list.id === "experience-list" ? "EXPERIENȚĂ" : "EDUCAȚIE";
    button.closest(".repeatable-item").remove();
    renumberRows(list, label);
});

form.addEventListener("input", updatePreview);

document.querySelectorAll('input[name="template"]').forEach((radio) => {
    radio.addEventListener("change", () => {
        document.querySelectorAll(".template-option").forEach((option) => {
            option.classList.toggle("selected", option.querySelector("input").checked);
        });
        preview.className = `cv-preview-card ${radio.value}`;
        const names = {
            europass: "EUROPASS-INSPIRED",
            ats: "ATS CLASSIC",
            modern: "MODERN MINIMAL",
        };
        document.querySelector("#preview-template").textContent = names[radio.value];
    });
});

updatePreview();
