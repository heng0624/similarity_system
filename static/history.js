 document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("historySearch");
    const filterSelect = document.getElementById("historyFilter");
    const tbody = document.querySelector("#historyTable tbody");

    if (!searchInput || !filterSelect || !tbody) {
        console.error("Required elements not found!");
        return;
    }

    function filterHistory() {
        const rows = Array.from(tbody.getElementsByTagName("tr")); // fetch fresh rows
        const searchText = searchInput.value.toLowerCase();
        const filterValue = filterSelect.value.toLowerCase();

        rows.forEach(row => {
            const mode = row.cells[1].innerText.toLowerCase();
            const allText = row.innerText.toLowerCase();

            const matchSearch = allText.includes(searchText);
            const matchFilter = filterValue === "" || mode === filterValue;

            row.style.display = (matchSearch && matchFilter) ? "" : "none";
        });
    }

    searchInput.addEventListener("keyup", filterHistory);
    filterSelect.addEventListener("change", filterHistory);
});

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("historySearch");
    const filterSelect = document.getElementById("historyFilter");
    const tbody = document.querySelector("#historyTable tbody");

    let currentPage = 1;
    const rowsPerPage = 5; // change as needed

    function getFilteredRows() {
        const rows = Array.from(tbody.getElementsByTagName("tr"));
        const searchText = searchInput.value.toLowerCase();
        const filterValue = filterSelect.value.toLowerCase();

        return rows.filter(row => {
            const mode = row.cells[1].innerText.toLowerCase();
            const allText = row.innerText.toLowerCase();

            const matchSearch = allText.includes(searchText);
            const matchFilter = filterValue === "" || mode === filterValue;

            return matchSearch && matchFilter;
        });
    }

    function showPage(page) {
        const rows = getFilteredRows();
        const totalPages = Math.ceil(rows.length / rowsPerPage);

        // Hide all first
        Array.from(tbody.getElementsByTagName("tr")).forEach(r => r.style.display = "none");

        // Show rows for current page
        const start = (page - 1) * rowsPerPage;
        const end = start + rowsPerPage;
        rows.slice(start, end).forEach(r => r.style.display = "");

        // Update page info
        document.getElementById("pageInfo").innerText = `Page ${page} of ${totalPages}`;

        // Disable/enable buttons
        document.getElementById("prevPage").disabled = page === 1;
        document.getElementById("nextPage").disabled = page === totalPages;
    }

    function filterAndPaginate() {
        currentPage = 1; // reset to first page
        showPage(currentPage);
    }

    searchInput.addEventListener("keyup", filterAndPaginate);
    filterSelect.addEventListener("change", filterAndPaginate);

    document.getElementById("prevPage").addEventListener("click", () => {
        currentPage--;
        showPage(currentPage);
    });

    document.getElementById("nextPage").addEventListener("click", () => {
        currentPage++;
        showPage(currentPage);
    });

    // Initial display
    showPage(currentPage);
});
