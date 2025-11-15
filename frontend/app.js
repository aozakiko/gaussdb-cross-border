const apiBaseInput = document.getElementById("apiBase");
const saveBaseBtn = document.getElementById("saveBase");
const createForm = document.getElementById("createForm");
const editForm = document.getElementById("editForm");
const editSection = document.getElementById("editSection");
const cancelEditBtn = document.getElementById("cancelEdit");
const recordsBody = document.getElementById("recordsBody");
const filterOwner = document.getElementById("filterOwner");
const filterStatus = document.getElementById("filterStatus");
const filterChannel = document.getElementById("filterChannel");
const filterDestination = document.getElementById("filterDestination");
const applyFiltersBtn = document.getElementById("applyFilters");
const analyticsOutput = document.getElementById("analyticsOutput");
const runAnalyticsBtn = document.getElementById("runAnalytics");
const toast = document.getElementById("toast");
const loadingIndicator = document.getElementById("loadingIndicator");
const metricTotal = document.getElementById("metricTotal");
const metricRevenue = document.getElementById("metricRevenue");
const metricTransit = document.getElementById("metricTransit");
const metricException = document.getElementById("metricException");
const lastUpdated = document.getElementById("lastUpdated");
const refreshBtn = document.getElementById("refreshRecords");
const statusChartCanvas = document.getElementById("statusChart");
const DEFAULT_LIMIT = 500;

let apiBase = localStorage.getItem("gauss_api_base") || "http://localhost:8000";
apiBaseInput.value = apiBase;
let statusChart;
let latestRecords = [];

const headers = { "Content-Type": "application/json" };

function notify(message, type = "info") {
  if (!toast) return;
  window.clearTimeout(notify.timer);
  toast.textContent = message;
  toast.dataset.state = type;
  toast.hidden = false;
  toast.classList.add("show");
  notify.timer = window.setTimeout(() => {
    toast.classList.remove("show");
    toast.hidden = true;
  }, 3600);
}

function setLoading(state) {
  if (!loadingIndicator) return;
  loadingIndicator.hidden = !state;
}

async function request(path, options = {}) {
  const endpoint = `${apiBase}${path}`;
  let response;
  try {
    response = await fetch(endpoint, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    throw new Error(`无法连接到 ${endpoint}，请检查 API 地址`);
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `请求失败 (${response.status})`);
  }
  if (response.status === 204) {
    return null;
  }
  return await response.json();
}

async function fetchRecords(options = {}) {
  const params = new URLSearchParams();
  if (filterOwner.value) params.append("owner", filterOwner.value);
  if (filterStatus.value) params.append("status", filterStatus.value);
  if (filterChannel?.value) params.append("channel", filterChannel.value);
  if (filterDestination?.value) params.append("destination", filterDestination.value);
  params.append("limit", DEFAULT_LIMIT.toString());
  const { showToast = false } = options;
  setLoading(true);
  try {
    const query = params.toString();
    const path = query ? `/records/?${query}` : "/records/";
    const data = await request(path);
    latestRecords = data.items || [];
    renderRecords(latestRecords);
    updateInsights(latestRecords);
    if (showToast) notify("数据已刷新", "success");
  } catch (error) {
    notify(error.message, "error");
    analyticsOutput.textContent = `无法连接 API: ${error.message}`;
    throw error;
  } finally {
    setLoading(false);
  }
}

function renderRecords(items = []) {
  recordsBody.innerHTML = "";
  if (!items.length) {
    recordsBody.innerHTML = `<tr><td colspan="9">暂无数据</td></tr>`;
    return;
  }
  items.forEach((record) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${record.order_number || record.id}</td>
      <td>${record.title}</td>
      <td>${record.sales_channel || "-"}</td>
      <td>${record.destination_market || "-"}</td>
      <td>${formatCurrency(record)}</td>
      <td><span class="badge badge-${record.status}">${formatStatus(record.status)}</span></td>
      <td>${record.owner || "-"}</td>
      <td>${record.order_date ? new Date(record.order_date).toLocaleDateString() : "-"}</td>
      <td>${record.tracking_number || "-"}</td>
      <td>
        <button class="ghost" data-action="edit" data-id="${record.id}">编辑</button>
        <button class="danger" data-action="delete" data-id="${record.id}">删除</button>
      </td>
    `;
    recordsBody.appendChild(tr);
  });
}

recordsBody.addEventListener("click", async (event) => {
  const action = event.target.dataset.action;
  if (!action) return;
  const id = Number(event.target.dataset.id);
  if (action === "edit") {
    const record = await request(`/records/${id}`);
    showEditForm(record);
  } else if (action === "delete") {
    if (confirm("确认删除该记录吗？")) {
      await request(`/records/${id}`, { method: "DELETE" });
      await fetchRecords();
      notify("记录已删除", "success");
    }
  }
});

function showEditForm(record) {
  editSection.hidden = false;
  for (const [key, value] of Object.entries(record)) {
    const field = editForm.elements.namedItem(key);
    if (field) field.value = value;
  }
}

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = Object.fromEntries(new FormData(createForm));
  formData.priority = Number(formData.priority) || 1;
  formData.order_amount = Number(formData.order_amount) || 0;
  try {
    await request("/records/", {
      method: "POST",
      body: JSON.stringify(formData),
    });
    createForm.reset();
    await fetchRecords();
    notify("记录已创建", "success");
  } catch (error) {
    notify(error.message, "error");
  }
});

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = Object.fromEntries(new FormData(editForm));
  const id = formData.id;
  delete formData.id;
  Object.keys(formData).forEach((key) => {
    if (formData[key] === "") delete formData[key];
  });
  if (formData.priority !== undefined) formData.priority = Number(formData.priority) || 1;
  if (formData.order_amount !== undefined) formData.order_amount = Number(formData.order_amount) || 0;
  try {
    await request(`/records/${id}`, {
      method: "PUT",
      body: JSON.stringify(formData),
    });
    editSection.hidden = true;
    await fetchRecords();
    notify("记录已更新", "success");
  } catch (error) {
    notify(error.message, "error");
  }
});

cancelEditBtn.addEventListener("click", () => {
  editSection.hidden = true;
});

applyFiltersBtn.addEventListener("click", fetchRecords);
runAnalyticsBtn.addEventListener("click", async () => {
  try {
    analyticsOutput.textContent = "运行中...";
    const data = await request("/records/analytics/spark");
    analyticsOutput.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    analyticsOutput.textContent = error.message;
    notify(error.message, "error");
  }
});

saveBaseBtn.addEventListener("click", () => {
  apiBase = apiBaseInput.value.replace(/\/$/, "");
  localStorage.setItem("gauss_api_base", apiBase);
  notify("API 地址已更新", "info");
  fetchRecords();
});

if (refreshBtn) {
  refreshBtn.addEventListener("click", () => fetchRecords({ showToast: true }));
}

function updateInsights(items = []) {
  const total = items.length;
  const inTransit = items.filter((item) => item.status === "in_transit").length;
  const exception = items.filter((item) => item.status === "exception").length;
  const revenue = items.reduce((sum, item) => sum + (Number(item.order_amount) || 0), 0);

  metricTotal.textContent = total;
  metricRevenue.textContent = revenue.toFixed(2);
  metricTransit.textContent = inTransit;
  metricException.textContent = exception;
  lastUpdated.textContent = `最近更新：${new Date().toLocaleString()}`;
  updateChart(items);
}

function updateChart(items = []) {
  if (!(window.Chart && statusChartCanvas)) return;
  const buckets = {
    awaiting_fulfillment: 0,
    picking: 0,
    in_transit: 0,
    delivered: 0,
    exception: 0,
  };
  items.forEach((item) => {
    if (buckets[item.status] === undefined) {
      buckets[item.status] = 0;
    }
    buckets[item.status] += 1;
  });
  const labelsMap = {
    awaiting_fulfillment: "待履约",
    picking: "拣货中",
    in_transit: "跨境在途",
    delivered: "已签收",
    exception: "异常",
  };
  const dataset = Object.entries(buckets).filter(([, count]) => count > 0);
  const labels = dataset.length ? dataset.map(([key]) => labelsMap[key] || key) : ["暂无数据"];
  const values = dataset.length ? dataset.map(([, count]) => count) : [1];
  const colors = ["#fde68a", "#bfdbfe", "#bbf7d0", "#fecdd3"];

  if (!statusChart) {
    statusChart = new Chart(statusChartCanvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
            borderWidth: 0,
          },
        ],
      },
      options: {
        plugins: {
          legend: { position: "bottom" },
        },
      },
    });
  } else {
    statusChart.data.labels = labels;
    statusChart.data.datasets[0].data = values;
    statusChart.update();
  }
}

function formatCurrency(record) {
  const amount = Number(record.order_amount);
  const currency = record.currency || "USD";
  if (Number.isNaN(amount)) return `${currency} -`;
  return `${currency} ${amount.toFixed(2)}`;
}

function formatStatus(status) {
  return (
    {
      awaiting_fulfillment: "待履约",
      picking: "拣货中",
      in_transit: "在途",
      delivered: "已签收",
      exception: "异常",
    }[status] || status
  );
}

fetchRecords().catch((error) => {
  analyticsOutput.textContent = `无法连接 API: ${error.message}`;
});
