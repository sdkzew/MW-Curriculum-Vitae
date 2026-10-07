document.querySelectorAll(".progress-fill").forEach((element) => {
    const percent = Math.max(0, Math.min(100, Number(element.dataset.percent) || 0));
    element.style.width = `${percent}%`;
});

document.querySelectorAll(".ring-fill").forEach((element) => {
    const target = element.getAttribute("stroke-dasharray");
    const score = Number.parseInt(element.dataset.score, 10);
    element.style.strokeDasharray = "0 314";
    element.style.stroke = score >= 75 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";
    window.setTimeout(() => {
        element.style.transition = "stroke-dasharray 1s ease";
        element.style.strokeDasharray = target;
    }, 100);
});
