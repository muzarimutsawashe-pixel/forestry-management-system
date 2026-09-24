/* ============================================================
   ALLIED TIMBERS ZIMBABWE
   FORESTRY MANAGEMENT SYSTEM
   FULL FRONTEND JAVASCRIPT
   ============================================================ */

const API_URL = "https://forestry-backend-vlyr.onrender.com/";
const SESSION_TIMEOUT_MS = 30 * 60 * 1000;


/* ============================================================
   AUTHENTICATED FETCH
============================================================ */

function apiFetch(url, options) {

    options = options || {};
    options.headers = options.headers || {};

    const token = localStorage.getItem("token");
    if (token) {
        options.headers["Authorization"] = "Bearer " + token;
    }

    return fetch(url, options).then(function (response) {
        if (response.status === 401) {
            localStorage.clear();
            window.location.href = "login.html?reason=timeout";
            throw new Error("Session expired");
        }
        return response;
    });
}


/* ============================================================
   SESSION TIMEOUT
============================================================ */

function checkSessionTimeout() {

    if (localStorage.getItem("loggedIn") !== "true") return;

    const last = parseInt(localStorage.getItem("lastActivity") || "0", 10);
    if (!last) return;

    if (Date.now() - last > SESSION_TIMEOUT_MS) {
        localStorage.clear();
        window.location.href = "login.html?reason=timeout";
    }
}

function touchSession() {
    if (localStorage.getItem("loggedIn") === "true") {
        localStorage.setItem("lastActivity", Date.now().toString());
    }
}

document.addEventListener("click",     touchSession, { passive: true });
document.addEventListener("keydown",   touchSession, { passive: true });
document.addEventListener("mousemove", touchSession, { passive: true });
document.addEventListener("scroll",    touchSession, { passive: true });

setInterval(checkSessionTimeout, 30 * 1000);


/* ============================================================
   ROLE-BASED UI
============================================================ */

const Permissions = (function () {

    const ROLE_LEVEL = {
        forester:           1,
        estate_manager:     2,
        production_manager: 3,
        admin:              4,
    };

    const ACTION_LEVEL = {
        view_dashboard:      1,
        view_compartments:   1,
        view_operations:     1,
        view_map:            1,
        view_statistics:     1,
        add_operation:       1,
        edit_operation:      1,
        delete_operation:    2,
        add_compartment:     2,
        edit_compartment:    2,
        delete_compartment:  2,
        view_all_estates:    3,
        manage_users:        4,
    };

    const role     = localStorage.getItem("role") || "";
    const level    = ROLE_LEVEL[role] || 0;
    const estateId = parseInt(localStorage.getItem("estate_id") || "0", 10) || null;

    function can(action) {
        return level >= (ACTION_LEVEL[action] || 0);
    }

    function prettify(r) {
        return {
            forester:           "Forester",
            estate_manager:     "Estate Manager",
            production_manager: "Production Manager",
            admin:              "Administrator",
        }[r] || r || "User";
    }

    function apply() {

        const roleEl = document.getElementById("displayRole");
        if (roleEl) roleEl.textContent = prettify(role);

        const sidebarRole = document.getElementById("sidebarRole");
        if (sidebarRole) sidebarRole.textContent = prettify(role);

        const addCpt = document.getElementById("addCompartmentButton");
        if (addCpt && !can("add_compartment")) {
            addCpt.style.display = "none";
        }

        const users = document.getElementById("usersSection");
        if (users && !can("manage_users")) {
            users.style.display = "none";
        }
    }

    return {
        can:      can,
        apply:    apply,
        role:     () => role,
        level:    () => level,
        estateId: () => estateId,
        prettify: prettify,
    };
})();


/* ============================================================
   APPLICATION STATE
============================================================ */

const State = {

    user: {
        username: localStorage.getItem("username") || "",
        role:     localStorage.getItem("role") || "",
        token:    localStorage.getItem("token") || ""
    },

    estates: [],

    allCompartments: [],

    filteredCompartments: [],

    selectedEstateId: null,

    editingCompartmentId: null,

    map: null,

    mapLayer: null

};


/* ============================================================
   START APPLICATION
============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    const estateSelect = document.getElementById("estateSelect");
    if (!estateSelect) return;

    console.log("========================================");
    console.log("ALLIED TIMBERS DASHBOARD STARTING");
    console.log("========================================");

    checkAuthentication();
    checkSessionTimeout();
    displayUser();
    Permissions.apply();
    setupDashboardEvents();
    setupSidebar();
    loadEstates();

});


/* ============================================================
   AUTHENTICATION
============================================================ */

function checkAuthentication() {

    const loggedIn = localStorage.getItem("loggedIn");
    const token    = localStorage.getItem("token");

    if (loggedIn !== "true" || !token) {
        window.location.href = "login.html";
    }
}


/* ============================================================
   DISPLAY LOGGED-IN USER
============================================================ */

function displayUser() {

    const username = State.user.username || "User";
    const role     = State.user.role || "User";

    const usernameElements = document.querySelectorAll(
        "#usernameDisplay, #currentUsername, .username-display"
    );
    usernameElements.forEach(function (element) {
        element.textContent = username;
    });

    const roleElements = document.querySelectorAll(
        "#roleDisplay, #currentRole, .role-display"
    );
    roleElements.forEach(function (element) {
        element.textContent = role;
    });
}


/* ============================================================
   DASHBOARD EVENTS
============================================================ */

function setupDashboardEvents() {

    /* ESTATE */

    const estateSelect = document.getElementById("estateSelect");
    if (estateSelect) {
        estateSelect.addEventListener("change", function () {
            const estateId = this.value;
            if (estateId) loadEstate(parseInt(estateId));
        });
    }

    /* SEARCH */

    const searchInput = document.getElementById("searchInput");
    if (searchInput) searchInput.addEventListener("input", applyFilters);

    /* YEAR */

    const filterYearPlanted = document.getElementById("filterYearPlanted");
    if (filterYearPlanted) {
        filterYearPlanted.addEventListener("input", applyFilters);
        filterYearPlanted.addEventListener("change", applyFilters);
    }

    /* SPECIES */

    const filterSpecies = document.getElementById("filterSpecies");
    if (filterSpecies) filterSpecies.addEventListener("change", applyFilters);

    /* BLOCK */

    const filterBlock = document.getElementById("filterBlock");
    if (filterBlock) filterBlock.addEventListener("change", applyFilters);

    /* STATUS */

    const filterStatus = document.getElementById("filterStatus");
    if (filterStatus) filterStatus.addEventListener("change", applyFilters);

    /* MIN AGE */

    const filterMinAge = document.getElementById("filterMinAge");
    if (filterMinAge) filterMinAge.addEventListener("input", applyFilters);

    /* MAX AGE */

    const filterMaxAge = document.getElementById("filterMaxAge");
    if (filterMaxAge) filterMaxAge.addEventListener("input", applyFilters);

    /* MIN AREA */

    const filterMinArea = document.getElementById("filterMinArea");
    if (filterMinArea) filterMinArea.addEventListener("input", applyFilters);

    /* MAX AREA */

    const filterMaxArea = document.getElementById("filterMaxArea");
    if (filterMaxArea) filterMaxArea.addEventListener("input", applyFilters);

    /* RESET */

    const resetButton = document.getElementById("resetFiltersButton");
    if (resetButton) resetButton.addEventListener("click", resetFilters);

    /* ADD COMPARTMENT */

    const addButton = document.getElementById("addCompartmentButton");
    if (addButton) addButton.addEventListener("click", openAddCompartmentModal);

    /* CLOSE MODAL */

    const closeButton = document.getElementById("modalCloseButton");
    if (closeButton) closeButton.addEventListener("click", closeCompartmentModal);

    /* CANCEL MODAL */

    const cancelButton = document.getElementById("cancelModalButton");
    if (cancelButton) cancelButton.addEventListener("click", closeCompartmentModal);

    /* FORM */

    const form = document.getElementById("compartmentForm");
    if (form) form.addEventListener("submit", saveCompartment);

    /* LOGOUT */

    const logoutButton = document.getElementById("logoutButton");
    if (logoutButton) logoutButton.addEventListener("click", logout);
}


/* ============================================================
   SIDEBAR
============================================================ */

function setupSidebar() {

    const sidebarLinks = document.querySelectorAll(
        ".sidebar a, .sidebar-link, [data-section]"
    );

    sidebarLinks.forEach(function (link) {
        link.addEventListener("click", function () {
            const target = this.getAttribute("data-section");
            if (!target) return;
            const section = document.getElementById(target);
            if (section) section.scrollIntoView({ behavior: "smooth" });
        });
    });
}


/* ============================================================
   LOAD ESTATES
============================================================ */

async function loadEstates() {

    try {

        console.log("Loading estates...");

        const response = await apiFetch(API_URL + "/api/estates");

        if (!response.ok) throw new Error("HTTP " + response.status);

        const result = await response.json();
        console.log("Estates response:", result);

        if (Array.isArray(result))               State.estates = result;
        else if (Array.isArray(result.estates))  State.estates = result.estates;
        else if (Array.isArray(result.data))     State.estates = result.data;
        else                                      State.estates = [];

        populateEstateSelect();

    } catch (error) {
        console.error("ERROR LOADING ESTATES:", error);
        showMessage("Unable to load estates.", "error");
    }
}


/* ============================================================
   POPULATE ESTATE SELECT
============================================================ */

function populateEstateSelect() {

    const select = document.getElementById("estateSelect");
    if (!select) return;

    select.innerHTML = '<option value="">Select Estate</option>';

    State.estates.forEach(function (estate) {
        const option = document.createElement("option");
        option.value = estate.estate_id;
        option.textContent = estate.estate_name;
        select.appendChild(option);
    });

    /* Lock non-production-managers / non-admins to their own estate */
    if (!Permissions.can("view_all_estates")) {

        const myEstate = Permissions.estateId();

        if (myEstate) {
            select.value = myEstate;
            select.disabled = true;
            loadEstate(myEstate);
        }

    } else {

        /* Production manager / admin: default to Martin (id 11) if present */
        const martin = State.estates.find(function (estate) {
            return Number(estate.estate_id) === 11;
        });

        if (martin) {
            select.value = "11";
            loadEstate(11);
        }
    }
}


/* ============================================================
   LOAD SELECTED ESTATE
============================================================ */

async function loadEstate(estateId) {

    State.selectedEstateId = Number(estateId);
    localStorage.setItem("selectedEstateId", State.selectedEstateId);

    updateCurrentEstate();
    await loadCompartments(State.selectedEstateId);
    await loadStatistics(State.selectedEstateId);
    await loadMap(State.selectedEstateId);
}


/* ============================================================
   UPDATE CURRENT ESTATE
============================================================ */

function updateCurrentEstate() {

    const estate = State.estates.find(function (item) {
        return Number(item.estate_id) === Number(State.selectedEstateId);
    });

    const name = estate ? estate.estate_name : "Current Estate";

    const elements = document.querySelectorAll("#currentEstate, #currentEstateName");
    elements.forEach(function (element) {
        element.textContent = name;
    });
}


/* ============================================================
   LOAD COMPARTMENTS
============================================================ */

async function loadCompartments(estateId) {

    console.log("Loading compartments. Estate ID:", estateId);

    try {

        const url = API_URL + "/api/estates/" + estateId + "/compartments";
        const response = await apiFetch(url);

        if (!response.ok) throw new Error("HTTP " + response.status);

        const raw = await response.json();

        if (Array.isArray(raw))                    State.allCompartments = raw;
        else if (Array.isArray(raw.compartments))  State.allCompartments = raw.compartments;
        else if (Array.isArray(raw.data))          State.allCompartments = raw.data;
        else if (Array.isArray(raw.results))       State.allCompartments = raw.results;
        else                                        State.allCompartments = [];

        State.filteredCompartments = [...State.allCompartments];

        console.log("Compartments received:", State.allCompartments.length);

        displayCompartments(State.allCompartments);
        populateFilters(State.allCompartments);
        updateDisplayedCount(State.allCompartments.length);

    } catch (error) {
        console.error("COMPARTMENTS ERROR:", error);
        State.allCompartments = [];
        State.filteredCompartments = [];
        displayCompartments([]);
        updateDisplayedCount(0);
    }
}


/* ============================================================
   DISPLAY COMPARTMENTS
============================================================ */

function displayCompartments(compartments) {

    const tableBody =
        document.getElementById("compartmentTableBody") ||
        document.querySelector("#compartmentsTable tbody") ||
        document.querySelector("table.data-table tbody") ||
        document.querySelector(".data-table > tbody");

    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (!compartments || compartments.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 9;
        cell.style.textAlign = "center";
        cell.style.padding = "30px";
        cell.textContent = "No compartments found.";
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
    }

    function pick(obj, keys) {
        for (let i = 0; i < keys.length; i++) {
            const value = obj[keys[i]];
            if (value !== null && value !== undefined && value !== "") return value;
        }
        return "";
    }

    const BLOCK_PATTERN = /^[A-Za-z]{1,2}$/;

    compartments.forEach(function (compartment) {

        const compartmentId = pick(compartment, ["compartment_id", "id", "cpt_id"]);
        const compartmentCode = pick(compartment, ["compartment_code", "code", "compartment", "cpt_code"]);

        let block = "";
        const rawBlock = pick(compartment, ["block_id", "block", "block_code"]);

        if (rawBlock !== "" && BLOCK_PATTERN.test(String(rawBlock).trim())) {
            block = String(rawBlock).trim().toUpperCase();
        }
        if (block === "" && compartmentCode !== "") {
            block = String(compartmentCode).trim().charAt(0).toUpperCase();
        }

        const species         = pick(compartment, ["species", "species_name"]);
        const plantingYear    = pick(compartment, ["planting_year", "year_planted", "year"]);
        const age             = pick(compartment, ["age"]);
        const areaPlanted     = pick(compartment, ["area_planted", "planted_area"]);
        const areaCompartment = pick(compartment, ["area_compartment", "total_area"]);
        const status          = pick(compartment, ["status"]);

        const row = document.createElement("tr");

        const cells = [
            { cls: "col-compartment", value: compartmentCode },
            { cls: "col-block",       value: block },
            { cls: "col-species",     value: species },
            { cls: "col-year",        value: plantingYear },
            { cls: "col-age",         value: age },
            { cls: "col-planted",     value: formatNumber(areaPlanted) },
            { cls: "col-total",       value: formatNumber(areaCompartment) },
            { cls: "col-status",      value: status },
        ];

        cells.forEach(function (cellData) {
            const td = document.createElement("td");
            td.className = cellData.cls;
            td.textContent = (cellData.value === null || cellData.value === undefined)
                ? "" : String(cellData.value);
            row.appendChild(td);
        });

        /* ACTIONS */

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions-cell";

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.textContent = "Edit";
        editButton.addEventListener("click", function () { editCompartment(compartmentId); });
        actionsCell.appendChild(editButton);

        if (Permissions.can("delete_compartment")) {
            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.textContent = "Delete";
            deleteButton.addEventListener("click", function () { deleteCompartment(compartmentId); });
            actionsCell.appendChild(deleteButton);
        }

        row.appendChild(actionsCell);
        tableBody.appendChild(row);

    });
}


/* ============================================================
   HTML SAFETY
============================================================ */

function escapeHTML(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* ============================================================
   NUMBER FORMAT
============================================================ */

function formatNumber(value) {
    if (value === null || value === undefined || value === "") return "";
    const number = Number(value);
    if (Number.isNaN(number)) return escapeHTML(value);
    return number.toLocaleString(undefined, { maximumFractionDigits: 2 });
}


/* ============================================================
   POPULATE FILTERS
============================================================ */

function populateFilters(compartments) {

    populateSelect("filterSpecies", compartments.map(function (item) { return item.species; }));

    populateSelect("filterBlock", compartments.map(function (item) {
        if (item.block_id) return item.block_id;
        const code = item.compartment_code || "";
        return code.charAt(0);
    }));

    populateSelect("filterStatus", compartments.map(function (item) { return item.status; }));
}


/* ============================================================
   POPULATE SELECT
============================================================ */

function populateSelect(elementId, values) {

    const select = document.getElementById(elementId);
    if (!select) return;

    const currentValue = select.value;
    const firstOption  = select.options[0] ? select.options[0].textContent : "All";

    const uniqueValues = [
        ...new Set(
            values
                .filter(function (value) {
                    return value !== null && value !== undefined && value !== "";
                })
                .map(function (value) { return String(value); })
        )
    ].sort();

    select.innerHTML = "";

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = firstOption || "All";
    select.appendChild(defaultOption);

    uniqueValues.forEach(function (value) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });

    if (uniqueValues.includes(currentValue)) select.value = currentValue;
}


/* ============================================================
   APPLY FILTERS
============================================================ */

function applyFilters() {

    const searchInput = document.getElementById("searchInput");
    const search = searchInput ? searchInput.value.trim().toLowerCase() : "";

    const yearElement     = document.getElementById("filterYearPlanted");
    const speciesElement  = document.getElementById("filterSpecies");
    const blockElement    = document.getElementById("filterBlock");
    const statusElement   = document.getElementById("filterStatus");
    const minAgeElement   = document.getElementById("filterMinAge");
    const maxAgeElement   = document.getElementById("filterMaxAge");
    const minAreaElement  = document.getElementById("filterMinArea");
    const maxAreaElement  = document.getElementById("filterMaxArea");

    const year    = yearElement ? yearElement.value.trim() : "";
    const species = speciesElement ? speciesElement.value : "";
    const block   = blockElement ? blockElement.value : "";
    const status  = statusElement ? statusElement.value : "";

    const minAge  = minAgeElement  && minAgeElement.value  !== "" ? Number(minAgeElement.value)  : null;
    const maxAge  = maxAgeElement  && maxAgeElement.value  !== "" ? Number(maxAgeElement.value)  : null;
    const minArea = minAreaElement && minAreaElement.value !== "" ? Number(minAreaElement.value) : null;
    const maxArea = maxAreaElement && maxAreaElement.value !== "" ? Number(maxAreaElement.value) : null;

    const filtered = State.allCompartments.filter(function (compartment) {

        if (search) {
            const code         = String(compartment.compartment_code ?? "").toLowerCase();
            const id           = String(compartment.compartment_id   ?? "").toLowerCase();
            const speciesValue = String(compartment.species          ?? "").toLowerCase();
            const blockValue   = String(
                compartment.block_id ??
                (compartment.compartment_code
                    ? String(compartment.compartment_code).charAt(0)
                    : "")
            ).toLowerCase();

            const matchesSearch =
                code.includes(search) ||
                id.includes(search) ||
                speciesValue.includes(search) ||
                blockValue.includes(search);

            if (!matchesSearch) return false;
        }

        if (year) {
            const plantingYear = String(compartment.planting_year ?? "");
            if (plantingYear !== year) return false;
        }

        if (species && String(compartment.species ?? "") !== species) return false;

        if (block) {
            const compartmentBlock =
                compartment.block_id ??
                (compartment.compartment_code
                    ? String(compartment.compartment_code).charAt(0)
                    : "");
            if (String(compartmentBlock) !== String(block)) return false;
        }

        if (status && String(compartment.status ?? "") !== status) return false;

        const age = Number(compartment.age);
        if (minAge !== null && !Number.isNaN(age) && age < minAge) return false;
        if (maxAge !== null && !Number.isNaN(age) && age > maxAge) return false;

        const area = Number(compartment.area_planted);
        if (minArea !== null && !Number.isNaN(area) && area < minArea) return false;
        if (maxArea !== null && !Number.isNaN(area) && area > maxArea) return false;

        return true;
    });

    State.filteredCompartments = filtered;

    displayCompartments(filtered);
    updateDisplayedCount(filtered.length);
    updateMapFromFilters();
}


/* ============================================================
   DISPLAY FILTERED COUNT
============================================================ */

function updateDisplayedCount(count) {

    const element = document.getElementById("displayedCompartmentCount");
    if (element) element.textContent = count;

    const total = document.getElementById("totalCompartmentCount");
    if (total) total.textContent = State.allCompartments.length;
}


/* ============================================================
   RESET FILTERS
============================================================ */

function resetFilters() {

    const ids = [
        "searchInput", "filterYearPlanted", "filterSpecies", "filterBlock",
        "filterStatus", "filterMinAge", "filterMaxAge", "filterMinArea", "filterMaxArea",
    ];

    ids.forEach(function (id) {
        const element = document.getElementById(id);
        if (element) element.value = "";
    });

    State.filteredCompartments = [...State.allCompartments];

    displayCompartments(State.allCompartments);
    updateDisplayedCount(State.allCompartments.length);
    updateMapFromFilters();
}


/* ============================================================
   LOAD STATISTICS
============================================================ */

async function loadStatistics(estateId) {

    try {
        const response = await apiFetch(
            API_URL + "/api/estates/" + estateId + "/statistics"
        );
        if (!response.ok) throw new Error("HTTP " + response.status);
        const statistics = await response.json();
        displayStatistics(statistics);
    } catch (error) {
        console.error("STATISTICS ERROR:", error);
        calculateLocalStatistics();
    }
}


function displayStatistics(statistics) {
    setText("totalCompartments", statistics.total_compartments ?? 0);
    setText("totalArea",         formatNumber(statistics.total_area ?? 0));
    setText("averageAge",        formatNumber(statistics.average_age ?? 0));
    setText("speciesCount",      statistics.species_count ?? 0);
}


function calculateLocalStatistics() {

    const compartments = State.allCompartments;

    let totalArea = 0;
    let totalAge  = 0;
    let ageCount  = 0;

    const species = new Set();

    compartments.forEach(function (item) {
        totalArea += Number(item.area_planted || 0);
        if (item.age !== null && item.age !== undefined && item.age !== "") {
            totalAge += Number(item.age);
            ageCount++;
        }
        if (item.species) species.add(item.species);
    });

    const averageAge = ageCount > 0 ? totalAge / ageCount : 0;

    setText("totalCompartments", compartments.length);
    setText("totalArea",         formatNumber(totalArea));
    setText("averageAge",        formatNumber(averageAge));
    setText("speciesCount",      species.size);
}


function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}


/* ============================================================
   LOAD MAP
============================================================ */

async function loadMap(estateId) {

    const mapElement = document.getElementById("map");
    if (!mapElement) return;

    try {
        const response = await apiFetch(API_URL + "/api/estates/" + estateId + "/map");
        if (!response.ok) throw new Error("HTTP " + response.status);
        const geojson = await response.json();
        initializeMap(geojson);
    } catch (error) {
        console.error("MAP ERROR:", error);
    }
}


function initializeMap(geojson) {

    const mapElement = document.getElementById("map");
    if (!mapElement) return;

    if (!State.map) {
        State.map = L.map("map");
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 22,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(State.map);
    }

    if (State.mapLayer) State.map.removeLayer(State.mapLayer);

    State.mapLayer = L.geoJSON(geojson, {
        style: function () { return { weight: 1, opacity: 1, fillOpacity: 0.25 }; },
        onEachFeature: function (feature, layer) {
            layer.on("click", function () { showMapCompartmentPopup(feature, layer); });
        },
    }).addTo(State.map);

    try {
        const bounds = State.mapLayer.getBounds();
        if (bounds.isValid()) State.map.fitBounds(bounds, { padding: [20, 20] });
    } catch (error) {
        console.warn("Unable to fit map bounds:", error);
    }

    setTimeout(function () { State.map.invalidateSize(); }, 300);

    updateMapFromFilters();
}


function findMapCompartment(feature) {

    if (!feature || !feature.properties) return null;

    const properties = feature.properties;

    const possibleIds = [
        properties.compartment_id, properties.id, properties.cpt_id, properties.cptId,
    ];

    for (const id of possibleIds) {
        if (id !== null && id !== undefined && id !== "") {
            const found = State.allCompartments.find(function (item) {
                return Number(item.compartment_id) === Number(id);
            });
            if (found) return found;
        }
    }

    const possibleCodes = [
        properties.compartment_code, properties.code, properties.compartment,
        properties.cpt_code, properties.cpt,
    ];

    for (const code of possibleCodes) {
        if (code !== null && code !== undefined && code !== "") {
            const normalCode = String(code).trim().toUpperCase();
            const found = State.allCompartments.find(function (item) {
                return String(item.compartment_code ?? "").trim().toUpperCase() === normalCode;
            });
            if (found) return found;
        }
    }

    return null;
}


function showMapCompartmentPopup(feature, layer) {

    const compartment = findMapCompartment(feature);

    if (compartment) {

        const code = compartment.compartment_code ?? "";
        const block = compartment.block_id ?? (code ? String(code).charAt(0) : "");

        const popup = `
            <div style="min-width:260px;">
                <h3 style="margin-top:0;">Compartment ${escapeHTML(code)}</h3>
                <hr>
                <p><strong>Compartment ID:</strong> ${escapeHTML(compartment.compartment_id)}</p>
                <p><strong>Block:</strong> ${escapeHTML(block)}</p>
                <p><strong>Species:</strong> ${escapeHTML(compartment.species)}</p>
                <p><strong>Year Planted:</strong> ${escapeHTML(compartment.planting_year)}</p>
                <p><strong>Age:</strong> ${escapeHTML(compartment.age)}</p>
                <p><strong>Planted Area:</strong> ${formatNumber(compartment.area_planted)} ha</p>
                <p><strong>Total Area:</strong> ${formatNumber(compartment.area_compartment)} ha</p>
                <p><strong>Status:</strong> ${escapeHTML(compartment.status)}</p>
                <p><strong>Estate ID:</strong> ${escapeHTML(compartment.estate_id)}</p>
            </div>
        `;

        layer.bindPopup(popup).openPopup();
        return;
    }

    const properties = feature && feature.properties ? feature.properties : {};

    let html = `<div style="min-width:240px;"><h3 style="margin-top:0;">Map Feature</h3><hr>`;

    Object.keys(properties).forEach(function (key) {
        html += `<p><strong>${escapeHTML(key)}:</strong> ${escapeHTML(properties[key])}</p>`;
    });

    html += `</div>`;

    layer.bindPopup(html).openPopup();
}


function getFilteredCompartmentsForMap() {
    return State.filteredCompartments || State.allCompartments;
}


function updateMapFromFilters() {

    if (!State.mapLayer) return;

    const filtered = getFilteredCompartmentsForMap();

    State.mapLayer.eachLayer(function (layer) {

        const compartment = findMapCompartment(layer.feature);

        if (!compartment) {
            updateSingleMapPolygonStyle(layer, false, false);
            return;
        }

        const isVisible = filtered.some(function (item) {
            return Number(item.compartment_id) === Number(compartment.compartment_id);
        });

        updateSingleMapPolygonStyle(layer, isVisible, true);
    });

    if (filtered.length === 1) {
        const target = filtered[0];
        State.mapLayer.eachLayer(function (layer) {
            const compartment = findMapCompartment(layer.feature);
            if (compartment && Number(compartment.compartment_id) === Number(target.compartment_id)) {
                try {
                    const bounds = layer.getBounds();
                    State.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17 });
                } catch (error) {
                    console.warn("Unable to zoom to compartment:", error);
                }
            }
        });
    }
}


function updateSingleMapPolygonStyle(layer, matching, identifiable) {

    if (!layer) return;

    if (matching && identifiable) {
        layer.setStyle({ weight: 3, opacity: 1, fillOpacity: 0.55 });
    } else {
        layer.setStyle({ weight: 1, opacity: 0.35, fillOpacity: 0.10 });
    }
}


/* ============================================================
   OPEN ADD COMPARTMENT MODAL
============================================================ */

function openAddCompartmentModal() {

    if (!Permissions.can("add_compartment")) {
        alert("You do not have permission to add compartments.");
        return;
    }

    State.editingCompartmentId = null;

    setText("modalTitle", "Add Compartment");

    const form = document.getElementById("compartmentForm");
    if (form) form.reset();

    const modal = document.getElementById("compartmentModal");
    if (modal) modal.style.display = "flex";
}


/* ============================================================
   EDIT COMPARTMENT
============================================================ */

function editCompartment(compartmentId) {

    const compartment = State.allCompartments.find(function (item) {
        return Number(item.compartment_id) === Number(compartmentId);
    });

    if (!compartment) {
        alert("Compartment could not be found.");
        return;
    }

    State.editingCompartmentId = Number(compartmentId);

    setText("modalTitle", "Edit Compartment");

    setValue("compartmentCode", compartment.compartment_code);
    setValue("species",         compartment.species);
    setValue("plantingYear",    compartment.planting_year);
    setValue("age",             compartment.age);
    setValue("areaPlanted",     compartment.area_planted);
    setValue("areaCompartment", compartment.area_compartment);
    setValue("blockId",         compartment.block_id);
    setValue("status",          compartment.status);

    const modal = document.getElementById("compartmentModal");
    if (modal) modal.style.display = "flex";
}


function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.value = value ?? "";
}


function closeCompartmentModal() {
    const modal = document.getElementById("compartmentModal");
    if (modal) modal.style.display = "none";
    State.editingCompartmentId = null;
}


/* ============================================================
   SAVE COMPARTMENT
============================================================ */

async function saveCompartment(event) {

    event.preventDefault();

    /* Only estate managers and above can write */
    if (!Permissions.can("add_compartment")) {
        alert("You do not have permission to save compartments.");
        return;
    }

    const estateId = State.selectedEstateId;
    if (!estateId || estateId <= 0) {
        alert("Please select an estate before saving the compartment.");
        return;
    }

    const compartmentCode = getValue("compartmentCode");
    const species         = getValue("species");
    const plantingYear    = getValue("plantingYear");
    const age             = getValue("age");
    const areaPlanted     = getValue("areaPlanted");
    const areaCompartment = getValue("areaCompartment");
    let   blockId         = getValue("blockId");
    const status          = getValue("status");

    if (!blockId && compartmentCode) {
        blockId = compartmentCode.trim().charAt(0).toUpperCase();
    }

    if (blockId && /^[0-9]+$/.test(String(blockId).trim()) && compartmentCode) {
        blockId = compartmentCode.trim().charAt(0).toUpperCase();
    }

    const data = {
        estate_id:        estateId,
        compartment_code: compartmentCode,
        species:          species || null,
        planting_year:    plantingYear ? Number(plantingYear) : null,
        area_planted:     areaPlanted ? Number(areaPlanted) : null,
        area_compartment: areaCompartment ? Number(areaCompartment) : null,
        status:           status || null,
        age:              age !== "" ? Number(age) : null,
        block_id:         blockId || null,
    };

    try {

        let url, method;

        if (State.editingCompartmentId) {
            url = API_URL + "/api/compartments/" + State.editingCompartmentId;
            method = "PUT";
        } else {
            url = API_URL + "/api/compartments";
            method = "POST";
        }

        const response = await apiFetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || result.message || "Unable to save compartment.");
        }

        alert(State.editingCompartmentId
            ? "Compartment updated successfully."
            : "Compartment added successfully.");

        closeCompartmentModal();
        await loadEstate(State.selectedEstateId);

    } catch (error) {
        console.error("SAVE COMPARTMENT ERROR:", error);
        alert("Unable to save compartment: " + error.message);
    }
}


function getValue(id) {
    const element = document.getElementById(id);
    if (!element) return "";
    return element.value.trim();
}


/* ============================================================
   DELETE COMPARTMENT
============================================================ */

async function deleteCompartment(compartmentId) {

    if (!Permissions.can("delete_compartment")) {
        alert("You do not have permission to delete compartments.");
        return;
    }

    const compartment = State.allCompartments.find(function (item) {
        return Number(item.compartment_id) === Number(compartmentId);
    });

    const code = compartment ? compartment.compartment_code : compartmentId;

    if (!confirm("Are you sure you want to delete compartment " + code + "?")) return;

    try {
        const response = await apiFetch(
            API_URL + "/api/compartments/" + compartmentId,
            { method: "DELETE" }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || result.message || "Unable to delete compartment.");
        }

        alert("Compartment deleted successfully.");
        await loadEstate(State.selectedEstateId);

    } catch (error) {
        console.error("DELETE ERROR:", error);
        alert(error.message);
    }
}


/* ============================================================
   LOGOUT
============================================================ */

function logout() {
    localStorage.clear();
    window.location.href = "login.html";
}


/* ============================================================
   GENERAL MESSAGE
============================================================ */

function showMessage(message, type) {
    console.log(type || "info", message);
}


/* ============================================================
   MAKE FUNCTIONS AVAILABLE TO HTML
============================================================ */

window.editCompartment         = editCompartment;
window.deleteCompartment       = deleteCompartment;
window.openAddCompartmentModal = openAddCompartmentModal;
window.closeCompartmentModal   = closeCompartmentModal;
window.applyFilters            = applyFilters;
window.resetFilters            = resetFilters;
window.logout                  = logout;


/* ============================================================
   END
   ============================================================ */

console.log("Allied Timbers Forestry Management System JS loaded.");