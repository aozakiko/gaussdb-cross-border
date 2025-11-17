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
const analyticsTotal = document.getElementById("analyticsTotal");
const analyticsEngine = document.getElementById("analyticsEngine");
const analyticsDetail = document.getElementById("analyticsDetail");
const analyticsStatusChartCanvas = document.getElementById("analyticsStatusChart");
const analyticsOwnerChartCanvas = document.getElementById("analyticsOwnerChart");
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
const ANALYTICS_COLORS = ["#2563eb", "#22c55e", "#f97316", "#ec4899", "#14b8a6", "#8b5cf6", "#0f172a"];

let apiBase = localStorage.getItem("gauss_api_base") || "http://localhost:8000";
apiBaseInput.value = apiBase;
let statusChart;
let analyticsStatusChart;
let analyticsOwnerChart;
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
    if (analyticsOutput) {
      analyticsOutput.hidden = false;
      analyticsOutput.textContent = `无法连接 API: ${error.message}`;
    }
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
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const id = Number(button.dataset.id);
  if (!Number.isFinite(id)) {
    notify("未找到记录 ID", "error");
    return;
  }
  if (action === "edit") {
    setLoading(true);
    try {
      const record = await request(`/records/${id}`);
      showEditForm(record);
      notify(`已加载记录 #${record.order_number || id}`, "info");
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  } else if (action === "delete") {
    if (confirm("确认删除该记录吗？")) {
      try {
        await request(`/records/${id}`, { method: "DELETE" });
        await fetchRecords();
        notify("记录已删除", "success");
      } catch (error) {
        notify(error.message, "error");
      }
    }
  }
});

function showEditForm(record) {
  if (!record) return;
  editForm.reset();
  for (const [key, value] of Object.entries(record)) {
    const field = editForm.elements.namedItem(key);
    if (!field) continue;
    field.value = value ?? "";
  }
  editSection.hidden = false;
  editSection.scrollIntoView({ behavior: "smooth", block: "start" });
  const firstField = editForm.querySelector("input[name='order_number']");
  if (firstField) firstField.focus();
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
if (runAnalyticsBtn) {
  runAnalyticsBtn.addEventListener("click", async () => {
    if (analyticsOutput) {
      analyticsOutput.hidden = false;
      analyticsOutput.textContent = "运行中...";
    }
    if (analyticsDetail) {
      analyticsDetail.textContent = "分析运行中...";
    }
    runAnalyticsBtn.disabled = true;
    try {
      const data = await request("/records/analytics/flink");
      renderAnalyticsView(data);
      notify("Flink 分析完成", "success");
    } catch (error) {
      if (analyticsDetail) {
        analyticsDetail.textContent = `分析失败：${error.message}`;
      }
      if (analyticsOutput) {
        analyticsOutput.hidden = false;
        analyticsOutput.textContent = error.message;
      }
      notify(error.message, "error");
    } finally {
      runAnalyticsBtn.disabled = false;
    }
  });
}

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

function renderAnalyticsView(payload) {
  if (!payload) return;

  if (analyticsTotal) {
    const total = Number(payload.total_records || 0);
    analyticsTotal.textContent = total.toLocaleString();
  }
  if (analyticsEngine) {
    analyticsEngine.textContent = payload.engine || "flink";
  }
  if (analyticsDetail) {
    analyticsDetail.textContent = payload.detail || "运行正常";
  }
  if (analyticsOutput) {
    analyticsOutput.textContent = JSON.stringify(payload, null, 2);
    analyticsOutput.hidden = true;
  }

  const statusEntries = Object.entries(payload.by_status || {});
  const statusLabels = statusEntries.length ? statusEntries.map(([key]) => formatStatus(key)) : ["暂无数据"];
  const statusValues = statusEntries.length ? statusEntries.map(([, value]) => value) : [1];
  analyticsStatusChart = mountAnalyticsChart(analyticsStatusChart, analyticsStatusChartCanvas, {
    type: "doughnut",
    labels: statusLabels,
    values: statusValues,
  });

  const ownerEntries = Object.entries(payload.by_owner || {});
  const ownerLabels = ownerEntries.length ? ownerEntries.map(([key]) => key) : ["暂无数据"];
  const ownerValues = ownerEntries.length ? ownerEntries.map(([, value]) => value) : [1];
  analyticsOwnerChart = mountAnalyticsChart(analyticsOwnerChart, analyticsOwnerChartCanvas, {
    type: "bar",
    labels: ownerLabels,
    values: ownerValues,
  });
}

function mountAnalyticsChart(instance, canvas, config) {
  if (!(canvas && window.Chart)) return instance;
  const colors = config.labels.map((_, idx) => ANALYTICS_COLORS[idx % ANALYTICS_COLORS.length]);
  const dataset = {
    label: "订单数",
    data: config.values,
    backgroundColor: colors,
    borderWidth: 0,
    borderRadius: config.type === "bar" ? 6 : 0,
  };

  const options = {
    plugins: {
      legend: { position: "bottom" },
    },
  };

  if (config.type === "bar") {
    options.indexAxis = "y";
    options.scales = {
      x: { beginAtZero: true, ticks: { precision: 0 } },
      y: { ticks: { autoSkip: false } },
    };
  }

  if (!instance) {
    return new Chart(canvas, {
      type: config.type,
      data: {
        labels: config.labels,
        datasets: [dataset],
      },
      options,
    });
  }

  instance.data.labels = config.labels;
  instance.data.datasets[0].data = config.values;
  instance.data.datasets[0].backgroundColor = colors;
  instance.update();
  return instance;
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
  if (analyticsOutput) {
    analyticsOutput.hidden = false;
    analyticsOutput.textContent = `无法连接 API: ${error.message}`;
  }
});
