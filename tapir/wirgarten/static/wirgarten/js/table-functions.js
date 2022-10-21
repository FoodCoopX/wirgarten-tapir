const rows = document.getElementsByClassName("tr-href");
for(const r of rows){
    r.style.cursor = "pointer";
    r.addEventListener("click", () => {
        window.document.location = r.getAttribute("href")
    });
}