// static/js/city.js

document.addEventListener("DOMContentLoaded", () => {
    const html = document.documentElement;
    const wrapper = document.querySelector(".city-wrapper");
    const selectMenu = document.getElementById("building-select");
    const toggleBtn = document.getElementById("toggleTheme");
    const tooltip = document.getElementById("cell-tooltip");

    // модалка удаления
    const deleteModal = document.getElementById("deleteModal");
    const modalConfirm = document.getElementById("modal-confirm");
    const modalCancel = document.getElementById("modal-cancel");
    let pendingDeleteCellId = null;

    // имя текущего пользователя (для "Мой дом")
    const currentUser = (document.body.dataset.username || "").trim();

    let selectedCellId = null;

    function getCells() {
        return Array.from(document.querySelectorAll(".city-grid .cell"));
    }

    // ---------- СТАТИСТИКА ----------
    const statOccupied = document.getElementById("stat-occupied");
    const statFree = document.getElementById("stat-free");
    const statLevel = document.getElementById("stat-level");

    function recalcStats() {
        const cells = getCells();
        if (!cells.length) return;

        const total = cells.length;
        // считаем по data-occupied
        const occupied = cells.filter(c => c.dataset.occupied === "1").length;
        const free = total - occupied;

        if (statOccupied) statOccupied.textContent = occupied;
        if (statFree) statFree.textContent = free;

        if (statLevel) {
            const level = total ? Math.round((occupied / total) * 100) : 0;
            statLevel.textContent = level + "%";
        }
    }
    recalcStats();

    // ---------- ТЕМА (day/night) ----------
    function saveTheme() {
        const theme = html.classList.contains("city-night") ? "night" : "day";
        localStorage.setItem("theme", theme);
    }

    function loadTheme() {
        return localStorage.getItem("theme") || "day";
    }

    function setDay() {
        html.classList.add("city-day");
        html.classList.remove("city-night");
        if (toggleBtn) toggleBtn.textContent = "🌙 Ночь";
        saveTheme();
    }

    function setNight() {
        html.classList.add("city-night");
        html.classList.remove("city-day");
        if (toggleBtn) toggleBtn.textContent = "☀️ День";
        saveTheme();
    }

    function initTheme() {
        const theme = loadTheme();
        if (theme === "night") setNight();
        else setDay();
    }
    initTheme();

    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            if (html.classList.contains("city-night")) setDay();
            else setNight();
        });
    }

    // ---------- СКРОЛЛ / АНИМАЦИЯ ПОСЛЕ POST ----------

    function focusCellByParam() {
        const urlParams = new URLSearchParams(window.location.search);
        const newCellId = urlParams.get("new_building");
        const removedCellId = urlParams.get("removed_cell");

        let targetId = newCellId || removedCellId;
        if (!targetId) return;

        const cell = document.querySelector(`.cell[data-cell-id="${targetId}"]`);
        if (!cell) return;

        // если дом только что построен – анимация
        if (newCellId && cell.classList.contains("occupied")) {
            cell.classList.add("built-on-load");
            setTimeout(() => cell.classList.remove("built-on-load"), 600);
        }

        // плавно проскроллить к ячейке
        cell.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        // убрать параметры из URL, чтобы анимация не повторялась
        const newUrl = window.location.pathname;
        history.replaceState({}, "", newUrl);
    }

    focusCellByParam();

    // ---------- МЕНЮ ВЫБОРА ДОМА (ПОД ЯЧЕЙКОЙ) ----------
    if (selectMenu && wrapper) {
        document.querySelectorAll(".cell.free").forEach(cell => {
            cell.addEventListener("click", (e) => {
                e.stopPropagation();
                selectedCellId = cell.dataset.cellId;

                selectMenu.classList.remove("hidden");
                selectMenu.style.visibility = "hidden";

                const wrapperRect = wrapper.getBoundingClientRect();
                const cellRect = cell.getBoundingClientRect();

                selectMenu.style.display = "flex";
                const menuRect = selectMenu.getBoundingClientRect();

                let left = cellRect.left - wrapperRect.left + cellRect.width / 2 - menuRect.width / 2;
                let top = cellRect.bottom - wrapperRect.top + 12;

                // держим меню в пределах карточки
                left = Math.max(12, Math.min(left, wrapperRect.width - menuRect.width - 12));
                top = Math.max(12, Math.min(top, wrapperRect.height - menuRect.height - 12));

                selectMenu.style.left = left + "px";
                selectMenu.style.top = top + "px";
                selectMenu.style.visibility = "visible";
            });
        });

        // выбор типа здания
        document.querySelectorAll(".building-option").forEach(option => {
            option.addEventListener("click", () => {
                const type = option.dataset.type;
                if (!selectedCellId) return;

                const form = document.createElement("form");
                form.method = "POST";
                form.action = `/cell/${selectedCellId}/build/${type}`;

                // прокидываем ТЕКУЩУЮ тему
                const themeInput = document.createElement("input");
                themeInput.type = "hidden";
                themeInput.name = "theme";
                themeInput.value = loadTheme();
                form.appendChild(themeInput);

                document.body.appendChild(form);
                form.submit();
            });
        });

        // клик вне меню — закрыть
        document.addEventListener("click", (e) => {
            if (!selectMenu.contains(e.target) && !e.target.closest(".cell.free")) {
                selectMenu.classList.add("hidden");
            }
        });
    }

    // ---------- МОДАЛКА УДАЛЕНИЯ ДОМА ----------
    function openDeleteModal(cellId) {
        pendingDeleteCellId = cellId;
        if (deleteModal) {
            deleteModal.classList.remove("hidden");
        }
    }

    function closeDeleteModal() {
        pendingDeleteCellId = null;
        if (deleteModal) {
            deleteModal.classList.add("hidden");
        }
    }

    if (modalCancel) {
        modalCancel.addEventListener("click", (e) => {
            e.preventDefault();
            closeDeleteModal();
        });
    }

    if (modalConfirm) {
        modalConfirm.addEventListener("click", (e) => {
            e.preventDefault();
            if (!pendingDeleteCellId) return;

            const form = document.createElement("form");
            form.method = "POST";
            form.action = `/cell/${pendingDeleteCellId}/toggle`;

            const themeInput = document.createElement("input");
            themeInput.type = "hidden";
            themeInput.name = "theme";
            themeInput.value = loadTheme();
            form.appendChild(themeInput);

            document.body.appendChild(form);
            closeDeleteModal();
            form.submit();
        });
    }

    // закрытие по клику по фону модалки
    if (deleteModal) {
        deleteModal.addEventListener("click", (e) => {
            if (e.target === deleteModal) {
                closeDeleteModal();
            }
        });
    }

    // ---------- КЛИК ПО ЗАНЯТОЙ ЯЧЕЙКЕ ----------
    document.querySelectorAll(".cell.occupied").forEach(cell => {
        cell.addEventListener("click", (e) => {
            e.preventDefault();

            const cellId = cell.dataset.cellId;
            const owner = (cell.dataset.owner || "").trim();
            const isOwn = owner === currentUser;

            // свои дома — через модалку подтверждения
            if (isOwn && deleteModal) {
                openDeleteModal(cellId);
                return;
            }

            // чужие ячейки — сразу отправляем форму
            const form = document.createElement("form");
            form.method = "POST";
            form.action = `/cell/${cellId}/toggle`;

            const themeInput = document.createElement("input");
            themeInput.type = "hidden";
            themeInput.name = "theme";
            themeInput.value = loadTheme();
            form.appendChild(themeInput);

            document.body.appendChild(form);
            form.submit();
        });
    });
// ---------- ПОДСКАЗКА "МОЙ ДОМ" / "ДОМ ПОЛЬЗОВАТЕЛЯ" ----------
    if (tooltip && wrapper) {
        getCells().forEach(cell => {
            cell.addEventListener("mouseenter", (e) => {
                const owner = (cell.dataset.owner || "").trim();

                if (owner && currentUser && owner === currentUser) {
                    tooltip.textContent = "Мой дом";
                } else if (owner) {
                    tooltip.textContent = `Дом пользователя: ${owner}`;
                } else {
                    tooltip.textContent = "Свободный участок";
                }

                tooltip.classList.remove("hidden");
                tooltip.classList.add("visible");

                const cellRect = cell.getBoundingClientRect();
                const wrapperRect = wrapper.getBoundingClientRect();
                const tooltipRect = tooltip.getBoundingClientRect();

                // Позиционируем тултип точно над ячейкой
                let left = cellRect.left - wrapperRect.left + cellRect.width / 2;
                let top = cellRect.top - wrapperRect.top - tooltipRect.height - 8;

                // Корректируем позицию, чтобы тултип не выходил за границы wrapper
                left = Math.max(tooltipRect.width / 2, 
                            Math.min(left, wrapperRect.width - tooltipRect.width / 2));
                top = Math.max(10, top);

                tooltip.style.left = left + "px";
                tooltip.style.top = top + "px";
                tooltip.style.transform = "translateX(-50%)";
            });

            cell.addEventListener("mouseleave", () => {
                tooltip.classList.add("hidden");
                tooltip.classList.remove("visible");
            });
        });
    }
    // ---------- АВТО-СКРЫТИЕ ФЛЕШ-СООБЩЕНИЙ ----------
    const flashes = document.querySelectorAll(".flash-message");
    if (flashes.length) {
        setTimeout(() => {
            flashes.forEach(msg => msg.classList.add("flash-hide"));
        }, 2000);
    }
});