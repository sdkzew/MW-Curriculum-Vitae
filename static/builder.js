const form = document.querySelector("#cv-builder");
const preview = document.querySelector("#cv-preview");
const profilePhoto = document.querySelector("#profile_photo");
const photoPreview = document.querySelector("#photo-preview");
const photoInitials = document.querySelector("#photo-initials");
const previewAvatarImage = document.querySelector("#preview-avatar-image");
const previewAvatarText = document.querySelector("#preview-avatar-text");
const removePhoto = document.querySelector("#remove-photo");

function textOrFallback(id, fallback) {
    const field = document.querySelector(`#${id}`);
    return field && field.value.trim() ? field.value.trim() : fallback;
}

function updatePreview() {
    document.querySelector("#preview-name").textContent = textOrFallback("full_name", form.dataset.nameFallback);
    document.querySelector("#preview-headline").textContent = textOrFallback("headline", form.dataset.titleFallback);
    document.querySelector("#preview-summary").textContent = textOrFallback(
        "summary",
        form.dataset.summaryFallback
    );
    const email = textOrFallback("email", form.dataset.emailFallback);
    const location = textOrFallback("location", form.dataset.locationFallback);
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
    addRow("experience-list", "experience-template", form.dataset.experienceLabel);
});

document.querySelector("#add-education").addEventListener("click", () => {
    addRow("education-list", "education-template", form.dataset.educationLabel);
});

form.addEventListener("click", (event) => {
    const button = event.target.closest(".remove-row");
    if (!button) return;
    const list = button.closest(".repeatable-list");
    const label = list.id === "experience-list" ? form.dataset.experienceLabel : form.dataset.educationLabel;
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

function clearPhoto() {
    profilePhoto.value = "";
    photoPreview.src = "";
    previewAvatarImage.src = "";
    photoPreview.hidden = true;
    previewAvatarImage.hidden = true;
    photoInitials.hidden = false;
    previewAvatarText.hidden = false;
    removePhoto.hidden = true;
}

profilePhoto.addEventListener("change", () => {
    const file = profilePhoto.files[0];
    if (!file) {
        clearPhoto();
        return;
    }
    const reader = new FileReader();
    reader.addEventListener("load", () => {
        photoPreview.src = reader.result;
        previewAvatarImage.src = reader.result;
        photoPreview.hidden = false;
        previewAvatarImage.hidden = false;
        photoInitials.hidden = true;
        previewAvatarText.hidden = true;
        removePhoto.hidden = false;
    });
    reader.readAsDataURL(file);
});

removePhoto.addEventListener("click", clearPhoto);

updatePreview();
