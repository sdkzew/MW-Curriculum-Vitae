const input = document.getElementById("cv_file");
const box = document.getElementById("upload-box");
const text = document.getElementById("upload-text");

function showSelectedFile(file) {
    text.replaceChildren();
    const strong = document.createElement("strong");
    strong.textContent = file.name;
    text.appendChild(strong);
    box.classList.add("has-file");
}

input.addEventListener("change", () => {
    if (input.files.length > 0) {
        showSelectedFile(input.files[0]);
    }
});

box.addEventListener("dragover", (event) => {
    event.preventDefault();
    box.classList.add("drag-over");
});
box.addEventListener("dragleave", () => box.classList.remove("drag-over"));
box.addEventListener("drop", (event) => {
    event.preventDefault();
    box.classList.remove("drag-over");
    if (event.dataTransfer.files.length > 0) {
        input.files = event.dataTransfer.files;
        showSelectedFile(event.dataTransfer.files[0]);
    }
});
