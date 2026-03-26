const TAB_CONFIG = {
  overview: {
    title: "Overview",
    description: "One line per container with state, health, image, release, and uptime.",
    endpoint: "/api/overview",
    columns: [
      { key: "container_name", label: "Container Name" },
      { key: "stack", label: "Stack" },
      { key: "running_state", label: "Container Running State" },
      { key: "health_status", label: "Health Status" },
      { key: "container_image", label: "Container Image" },
      { key: "container_release", label: "Container Release" },
      { key: "uptime", label: "Uptime", sortKey: "uptime_sort" },
    ],
  },
  resources: {
    title: "Resources",
    description: "One line per container with current CPU, memory, network, and disk usage.",
    endpoint: "/api/resources",
    columns: [
      { key: "container_name", label: "Container Name" },
      { key: "current_cpu_usage", label: "Current CPU Usage", sortKey: "cpu_sort" },
      { key: "current_memory_usage", label: "Current Memory Usage", sortKey: "memory_sort" },
      { key: "current_network_rx_usage", label: "Current Network RX Usage", sortKey: "network_rx_sort" },
      { key: "current_network_tx_usage", label: "Current Network TX Usage", sortKey: "network_tx_sort" },
      { key: "current_disk_usage", label: "Current Disk Usage", sortKey: "disk_sort" },
    ],
  },
  ports: {
    title: "Ports",
    description: "One line per published or exposed port.",
    endpoint: "/api/ports",
    columns: [
      { key: "container_name", label: "Container Name" },
      { key: "network", label: "Network" },
      { key: "internal_port", label: "Internal Port", sortKey: "internal_port_sort" },
      { key: "external_port", label: "External Port", sortKey: "external_port_sort" },
    ],
  },
  mounts: {
    title: "Mounts",
    description: "One line per container mount.",
    endpoint: "/api/mounts",
    columns: [
      { key: "container_name", label: "Container Name" },
      { key: "mount_type", label: "Mount Type" },
      { key: "internal_path", label: "Internal Path" },
      { key: "external_path", label: "External Path" },
    ],
  },
};

const state = {
  activeTab: "overview",
  datasets: {},
  generatedAt: {},
  sorts: {},
  filters: {},
};

const tableHead = document.querySelector("#data-table thead");
const tableBody = document.querySelector("#data-table tbody");
const filtersContainer = document.getElementById("filters");
const messageBanner = document.getElementById("message-banner");
const rowCount = document.getElementById("row-count");
const updatedAt = document.getElementById("updated-at");
const tabTitle = document.getElementById("tab-title");
const tabDescription = document.getElementById("tab-description");
const refreshButton = document.getElementById("refresh-button");

function defaultSortFor(tabName) {
  const firstColumn = TAB_CONFIG[tabName].columns[0];
  return { key: firstColumn.key, direction: "asc" };
}

function getSort(tabName) {
  if (!state.sorts[tabName]) {
    state.sorts[tabName] = defaultSortFor(tabName);
  }
  return state.sorts[tabName];
}

function getFilters(tabName) {
  if (!state.filters[tabName]) {
    state.filters[tabName] = {};
  }
  return state.filters[tabName];
}

function setMessage(text, kind = "info") {
  if (!text) {
    messageBanner.textContent = "";
    messageBanner.className = "message-banner is-hidden";
    return;
  }
  messageBanner.textContent = text;
  messageBanner.className = `message-banner ${kind}`;
}

function formatTimestamp(value) {
  if (!value) {
    return "Not loaded";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function compareValues(left, right) {
  if (typeof left === "number" && typeof right === "number") {
    return left - right;
  }
  return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
}

function applyFilters(tabName, rows) {
  const filters = getFilters(tabName);
  return rows.filter((row) =>
    Object.entries(filters).every(([key, value]) => !value || String(row[key] ?? "") === value),
  );
}

function sortRows(tabName, rows) {
  const config = TAB_CONFIG[tabName];
  const columnsByKey = Object.fromEntries(config.columns.map((column) => [column.key, column]));
  const sort = getSort(tabName);
  const column = columnsByKey[sort.key] || config.columns[0];
  const sortKey = column.sortKey || column.key;
  const orderedRows = [...rows].sort((left, right) => {
    const result = compareValues(left[sortKey] ?? left[column.key] ?? "", right[sortKey] ?? right[column.key] ?? "");
    return sort.direction === "asc" ? result : -result;
  });
  return orderedRows;
}

function renderFilters(tabName, rows) {
  const config = TAB_CONFIG[tabName];
  const filters = getFilters(tabName);
  filtersContainer.innerHTML = "";

  config.columns.forEach((column) => {
    const wrapper = document.createElement("label");
    wrapper.className = "filter-control";

    const label = document.createElement("span");
    label.textContent = column.label;

    const select = document.createElement("select");
    select.innerHTML = `<option value="">All ${column.label}</option>`;
    const values = [...new Set(rows.map((row) => String(row[column.key] ?? "")).filter(Boolean))].sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }),
    );
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    select.value = filters[column.key] || "";
    select.addEventListener("change", () => {
      filters[column.key] = select.value;
      renderBody(tabName);
    });

    wrapper.appendChild(label);
    wrapper.appendChild(select);
    filtersContainer.appendChild(wrapper);
  });
}

function renderHeader(tabName) {
  const config = TAB_CONFIG[tabName];
  const sort = getSort(tabName);
  tableHead.innerHTML = "";
  const row = document.createElement("tr");

  config.columns.forEach((column) => {
    const header = document.createElement("th");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "header-button";
    const isActive = sort.key === column.key;
    const direction = isActive ? (sort.direction === "asc" ? " ▲" : " ▼") : "";
    button.textContent = `${column.label}${direction}`;
    button.addEventListener("click", () => {
      if (sort.key === column.key) {
        sort.direction = sort.direction === "asc" ? "desc" : "asc";
      } else {
        sort.key = column.key;
        sort.direction = "asc";
      }
      renderHeader(tabName);
      renderBody(tabName);
    });
    header.appendChild(button);
    row.appendChild(header);
  });

  tableHead.appendChild(row);
}

function renderBody(tabName) {
  const config = TAB_CONFIG[tabName];
  const filteredRows = applyFilters(tabName, state.datasets[tabName] || []);
  const orderedRows = sortRows(tabName, filteredRows);
  tableBody.innerHTML = "";

  if (!orderedRows.length) {
    const emptyRow = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = config.columns.length;
    cell.className = "empty-state";
    cell.textContent = "No rows match the current filter set.";
    emptyRow.appendChild(cell);
    tableBody.appendChild(emptyRow);
  } else {
    orderedRows.forEach((entry) => {
      const row = document.createElement("tr");
      config.columns.forEach((column) => {
        const cell = document.createElement("td");
        cell.textContent = String(entry[column.key] ?? "-");
        row.appendChild(cell);
      });
      tableBody.appendChild(row);
    });
  }

  rowCount.textContent = `${orderedRows.length} row${orderedRows.length === 1 ? "" : "s"}`;
  updatedAt.textContent = formatTimestamp(state.generatedAt[tabName]);
}

async function loadTab(tabName) {
  state.activeTab = tabName;
  const config = TAB_CONFIG[tabName];
  tabTitle.textContent = config.title;
  tabDescription.textContent = config.description;
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === tabName);
  });

  setMessage(`Loading ${config.title.toLowerCase()} data...`);

  try {
    const response = await fetch(config.endpoint, { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.detail || `Request failed with status ${response.status}`);
    }
    state.datasets[tabName] = Array.isArray(payload.rows) ? payload.rows : [];
    state.generatedAt[tabName] = payload.generated_at || null;
    state.sorts[tabName] = defaultSortFor(tabName);
    state.filters[tabName] = {};
    renderFilters(tabName, state.datasets[tabName]);
    renderHeader(tabName);
    renderBody(tabName);
    setMessage("", "info");
  } catch (error) {
    state.datasets[tabName] = [];
    state.generatedAt[tabName] = null;
    renderFilters(tabName, []);
    renderHeader(tabName);
    renderBody(tabName);
    setMessage(error instanceof Error ? error.message : "Failed to load data.", "error");
  }
}

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    const { tab } = button.dataset;
    if (tab) {
      void loadTab(tab);
    }
  });
});

refreshButton.addEventListener("click", () => {
  void loadTab(state.activeTab);
});

document.addEventListener("DOMContentLoaded", () => {
  void loadTab("overview");
});
