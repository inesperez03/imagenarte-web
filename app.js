const PAGE_SIZE = 12;

const sampleProducts = [
  {
    id: crypto.randomUUID(),
    title: "Mediterráneo Dorado",
    type: "Paisaje",
    colors: ["Azul", "Dorado", "Blanco"],
    groups: ["Mediterráneo", "Clásico"],
    size: "80 x 100 cm",
    price: 420,
    description: "Pieza luminosa con presencia decorativa para salón o despacho.",
    image: "",
    available: true,
    published: true,
    createdAt: "2026-08-18T10:00:00.000Z",
  },
  {
    id: crypto.randomUUID(),
    title: "Composición Serena",
    type: "Abstracto",
    colors: ["Verde", "Negro", "Arena"],
    groups: ["Moderno", "Texturas"],
    size: "70 x 90 cm",
    price: 360,
    description: "Obra abstracta en tonos naturales con acabado elegante.",
    image: "",
    available: true,
    published: true,
    createdAt: "2026-08-20T10:00:00.000Z",
  },
  {
    id: crypto.randomUUID(),
    title: "Lámina Botánica",
    type: "Lámina",
    colors: ["Verde", "Blanco", "Madera"],
    groups: ["Botánico", "Enmarcado"],
    size: "50 x 70 cm",
    price: 145,
    description: "Lámina decorativa con marco cálido y passepartout claro.",
    image: "",
    available: true,
    published: true,
    createdAt: "2026-08-22T10:00:00.000Z",
  },
  {
    id: crypto.randomUUID(),
    title: "Rojo Interior",
    type: "Óleo",
    colors: ["Rojo", "Terracota", "Negro"],
    groups: ["Contemporáneo", "Color"],
    size: "90 x 90 cm",
    price: 510,
    description: "Óleo con contraste intenso para espacios con personalidad.",
    image: "",
    available: true,
    published: true,
    createdAt: "2026-08-25T10:00:00.000Z",
  },
];

const state = {
  products: [],
  tags: {
    types: [],
    colors: [],
    groups: [],
  },
  filters: {
    search: "",
    type: "Todos",
    color: "Todos",
    group: "Todos",
    sort: "recent",
  },
  currentPage: 1,
  adminUnlocked: false,
  adminPassword: "",
};

const els = {
  productGrid: document.querySelector("#productGrid"),
  resultCount: document.querySelector("#resultCount"),
  pageStatus: document.querySelector("#pageStatus"),
  pagination: document.querySelector("#pagination"),
  searchInput: document.querySelector("#searchInput"),
  typeFilter: document.querySelector("#typeFilter"),
  colorFilter: document.querySelector("#colorFilter"),
  groupFilter: document.querySelector("#groupFilter"),
  sortSelect: document.querySelector("#sortSelect"),
  resetFilters: document.querySelector("#resetFilters"),
  adminDialog: document.querySelector("#adminDialog"),
  loginPanel: document.querySelector("#loginPanel"),
  adminPanel: document.querySelector("#adminPanel"),
  loginForm: document.querySelector("#loginForm"),
  passwordInput: document.querySelector("#passwordInput"),
  productForm: document.querySelector("#productForm"),
  productId: document.querySelector("#productId"),
  imageInput: document.querySelector("#imageInput"),
  titleInput: document.querySelector("#titleInput"),
  typeInput: document.querySelector("#typeInput"),
  colorsInput: document.querySelector("#colorsInput"),
  groupsInput: document.querySelector("#groupsInput"),
  sizeInput: document.querySelector("#sizeInput"),
  priceInput: document.querySelector("#priceInput"),
  descriptionInput: document.querySelector("#descriptionInput"),
  availableInput: document.querySelector("#availableInput"),
  publishedInput: document.querySelector("#publishedInput"),
  tagForm: document.querySelector("#tagForm"),
  tagKindInput: document.querySelector("#tagKindInput"),
  tagNameInput: document.querySelector("#tagNameInput"),
  tagManagerLists: document.querySelector("#tagManagerLists"),
  adminProducts: document.querySelector("#adminProducts"),
  clearForm: document.querySelector("#clearForm"),
};

async function loadProducts(includeAll = false) {
  const response = await fetch(`/api/products${includeAll ? "?all=1" : ""}`, {
    headers: includeAll ? adminHeaders() : {},
  });
  if (!response.ok) throw new Error("No se han podido cargar los productos.");
  const data = await response.json();
  state.products = data.products;
}

async function loadTags() {
  const response = await fetch("/api/tags");
  if (!response.ok) throw new Error("No se han podido cargar las etiquetas.");
  const data = await response.json();
  state.tags = data.tags;
}

function uniqueOptions(key) {
  const values = state.products.flatMap((product) => product[key] || []);
  return ["Todos", ...Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, "es"))];
}

function renderSelect(select, options, selected) {
  select.innerHTML = options
    .map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`)
    .join("");
  select.value = options.includes(selected) ? selected : "Todos";
}

function syncFilterOptions() {
  renderSelect(els.typeFilter, ["Todos", ...state.tags.types], state.filters.type);
  renderSelect(els.colorFilter, ["Todos", ...state.tags.colors], state.filters.color);
  renderSelect(els.groupFilter, ["Todos", ...state.tags.groups], state.filters.group);
  renderAdminTagInputs();
  renderTagManagerLists();
}

function getFilteredProducts() {
  const search = state.filters.search.trim().toLowerCase();
  const visible = state.products.filter((product) => {
    if (!product.published) return false;
    const text = [
      product.title,
      product.description,
      product.type,
      product.size,
      ...(product.colors || []),
      ...(product.groups || []),
    ]
      .join(" ")
      .toLowerCase();

    return (
      (!search || text.includes(search)) &&
      (state.filters.type === "Todos" || product.type === state.filters.type) &&
      (state.filters.color === "Todos" || product.colors.includes(state.filters.color)) &&
      (state.filters.group === "Todos" || product.groups.includes(state.filters.group))
    );
  });

  return visible.sort((a, b) => {
    if (state.filters.sort === "title") return a.title.localeCompare(b.title, "es");
    if (state.filters.sort === "priceAsc") return Number(a.price || 0) - Number(b.price || 0);
    if (state.filters.sort === "priceDesc") return Number(b.price || 0) - Number(a.price || 0);
    return new Date(b.createdAt) - new Date(a.createdAt);
  });
}

function renderProducts() {
  const products = getFilteredProducts();
  const totalPages = Math.max(1, Math.ceil(products.length / PAGE_SIZE));
  if (state.currentPage > totalPages) state.currentPage = totalPages;
  const start = (state.currentPage - 1) * PAGE_SIZE;
  const paginatedProducts = products.slice(start, start + PAGE_SIZE);

  els.resultCount.textContent = `${products.length} ${products.length === 1 ? "cuadro encontrado" : "cuadros encontrados"}`;
  els.pageStatus.textContent = products.length ? `Página ${state.currentPage} de ${totalPages}` : "";

  if (!products.length) {
    els.productGrid.innerHTML = `<div class="empty-state">No hay cuadros que coincidan con esos filtros.</div>`;
    els.pagination.innerHTML = "";
    return;
  }

  els.productGrid.innerHTML = paginatedProducts.map(renderProductCard).join("");
  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  if (totalPages <= 1) {
    els.pagination.innerHTML = "";
    return;
  }

  const buttons = [];
  buttons.push(`
    <button class="page-button" type="button" data-page="${state.currentPage - 1}" ${state.currentPage === 1 ? "disabled" : ""}>
      Anterior
    </button>
  `);

  for (let page = 1; page <= totalPages; page += 1) {
    if (page === 1 || page === totalPages || Math.abs(page - state.currentPage) <= 2) {
      buttons.push(`
        <button class="page-button ${page === state.currentPage ? "active" : ""}" type="button" data-page="${page}">
          ${page}
        </button>
      `);
    } else if (Math.abs(page - state.currentPage) === 3) {
      buttons.push(`<button class="page-button" type="button" disabled>...</button>`);
    }
  }

  buttons.push(`
    <button class="page-button" type="button" data-page="${state.currentPage + 1}" ${state.currentPage === totalPages ? "disabled" : ""}>
      Siguiente
    </button>
  `);

  els.pagination.innerHTML = buttons.join("");
}

function renderProductCard(product) {
  const image = product.image || generatedArtwork(product);
  const price = product.price ? `${Number(product.price).toLocaleString("es-ES")} €` : "Consultar precio";
  const tags = [...product.colors, ...product.groups]
    .slice(0, 5)
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");

  return `
    <article class="product-card">
      <div class="product-image">
        <img src="${image}" alt="${escapeHtml(product.title)}" loading="lazy">
        <span class="stock-badge">${product.available ? "Disponible" : "Reservado"}</span>
      </div>
      <div class="product-info">
        <div>
          <h3>${escapeHtml(product.title)}</h3>
          <div class="product-meta">
            <span>${escapeHtml(product.type)}</span>
            ${product.size ? `<span>${escapeHtml(product.size)}</span>` : ""}
          </div>
        </div>
        <p>${escapeHtml(product.description || "Pieza disponible en tienda.")}</p>
        <div class="tag-row">${tags}</div>
        <div class="price">${price}</div>
      </div>
    </article>
  `;
}

function generatedArtwork(product) {
  const palette = product.colors.join(" ");
  const hue = Math.abs(hashCode(palette || product.title)) % 360;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000">
      <rect width="800" height="1000" fill="hsl(${hue}, 28%, 84%)"/>
      <rect x="80" y="80" width="640" height="840" fill="white"/>
      <rect x="122" y="122" width="556" height="756" fill="hsl(${hue}, 35%, 32%)"/>
      <circle cx="280" cy="320" r="136" fill="hsl(${(hue + 48) % 360}, 55%, 64%)"/>
      <path d="M145 790 C260 545 405 610 482 410 C545 245 640 248 678 215 L678 878 L145 878 Z" fill="hsl(${(hue + 118) % 360}, 34%, 42%)"/>
      <path d="M122 705 L678 520 L678 878 L122 878 Z" fill="hsla(${(hue + 210) % 360}, 45%, 25%, .65)"/>
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function hashCode(value) {
  return value.split("").reduce((hash, char) => (hash << 5) - hash + char.charCodeAt(0), 0);
}

function renderAdminProducts() {
  if (!state.products.length) {
    els.adminProducts.innerHTML = `<div class="empty-state">Todavía no hay productos.</div>`;
    return;
  }

  els.adminProducts.innerHTML = state.products
    .map((product) => {
      const image = product.image || generatedArtwork(product);
      return `
        <article class="admin-item">
          <img src="${image}" alt="">
          <div>
            <h3>${escapeHtml(product.title)}</h3>
            <div class="product-meta">
              <span>${escapeHtml(product.type)}</span>
              <span>${product.published ? "Publicado" : "Oculto"}</span>
              <span>${product.available ? "Disponible" : "Reservado"}</span>
            </div>
          </div>
          <div class="admin-actions">
            <button class="secondary-button" type="button" data-edit="${product.id}">Editar</button>
            <button class="secondary-button" type="button" data-delete="${product.id}">Eliminar</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function resetForm() {
  els.productForm.reset();
  els.productId.value = "";
  els.availableInput.checked = true;
  els.publishedInput.checked = true;
  setCheckedTags(els.colorsInput, []);
  setCheckedTags(els.groupsInput, []);
}

function fillForm(product) {
  els.productId.value = product.id;
  els.titleInput.value = product.title;
  els.typeInput.value = product.type;
  setCheckedTags(els.colorsInput, product.colors);
  setCheckedTags(els.groupsInput, product.groups);
  els.sizeInput.value = product.size || "";
  els.priceInput.value = product.price || "";
  els.descriptionInput.value = product.description || "";
  els.availableInput.checked = product.available;
  els.publishedInput.checked = product.published;
  els.imageInput.value = "";
  els.titleInput.focus();
}

async function handleProductSubmit(event) {
  event.preventDefault();

  const id = els.productId.value;
  const formData = new FormData();
  formData.append("title", els.titleInput.value.trim());
  formData.append("type", els.typeInput.value);
  formData.append("colors", getCheckedTags(els.colorsInput).join(", "));
  formData.append("groups", getCheckedTags(els.groupsInput).join(", "));
  formData.append("size", els.sizeInput.value.trim());
  formData.append("price", els.priceInput.value.trim());
  formData.append("description", els.descriptionInput.value.trim());
  formData.append("available", String(els.availableInput.checked));
  formData.append("published", String(els.publishedInput.checked));
  if (els.imageInput.files[0]) formData.append("image", els.imageInput.files[0]);

  const response = await fetch(id ? `/api/products/${encodeURIComponent(id)}` : "/api/products", {
    method: id ? "PUT" : "POST",
    headers: adminHeaders(),
    body: formData,
  });

  if (!response.ok) {
    alert("No se ha podido guardar el producto.");
    return;
  }

  resetForm();
  await refreshProducts(true);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function unlockAdmin(password) {
  state.adminPassword = password;
  const response = await fetch("/api/login", {
    method: "POST",
    headers: adminHeaders(),
  });

  if (!response.ok) {
    state.adminPassword = "";
    els.passwordInput.setCustomValidity("Contraseña incorrecta");
    els.passwordInput.reportValidity();
    els.passwordInput.setCustomValidity("");
    return;
  }

  try {
    await refreshProducts(true);
  } catch {
    state.adminPassword = "";
    alert("La contraseña es correcta, pero no se han podido cargar los datos de gestión. Revisa Supabase o Render.");
    return;
  }

  state.adminUnlocked = true;
  els.loginPanel.classList.add("hidden");
  els.adminPanel.classList.remove("hidden");
  els.passwordInput.value = "";
}

function bindEvents() {
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      switchView(button.dataset.viewTarget);
    });
  });

  document.querySelectorAll("[data-open-admin]").forEach((button) => {
    button.addEventListener("click", () => els.adminDialog.showModal());
  });

  document.querySelector("[data-close-admin]").addEventListener("click", () => {
    els.adminDialog.close();
  });

  els.loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    unlockAdmin(els.passwordInput.value);
  });

  els.searchInput.addEventListener("input", (event) => {
    state.filters.search = event.target.value;
    state.currentPage = 1;
    renderProducts();
  });

  [
    [els.typeFilter, "type"],
    [els.colorFilter, "color"],
    [els.groupFilter, "group"],
    [els.sortSelect, "sort"],
  ].forEach(([element, key]) => {
    element.addEventListener("change", (event) => {
      state.filters[key] = event.target.value;
      state.currentPage = 1;
      renderProducts();
    });
  });

  els.resetFilters.addEventListener("click", () => {
    state.filters = { search: "", type: "Todos", color: "Todos", group: "Todos", sort: "recent" };
    state.currentPage = 1;
    els.searchInput.value = "";
    els.sortSelect.value = "recent";
    syncFilterOptions();
    renderProducts();
  });

  els.pagination.addEventListener("click", (event) => {
    const page = Number(event.target.dataset.page);
    if (!page || page === state.currentPage) return;
    state.currentPage = page;
    renderProducts();
    document.querySelector("#view-escaparate").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  els.productForm.addEventListener("submit", handleProductSubmit);
  els.clearForm.addEventListener("click", resetForm);
  els.tagForm.addEventListener("submit", handleTagSubmit);

  els.adminProducts.addEventListener("click", (event) => {
    const editId = event.target.dataset.edit;
    const deleteId = event.target.dataset.delete;

    if (editId) {
      const product = state.products.find((item) => item.id === editId);
      if (product) fillForm(product);
    }

    if (deleteId && confirm("¿Eliminar este producto del escaparate?")) {
      deleteProduct(deleteId);
    }
  });
}

async function deleteProduct(productId) {
  const response = await fetch(`/api/products/${encodeURIComponent(productId)}`, {
    method: "DELETE",
    headers: adminHeaders(),
  });
  if (!response.ok) {
    alert("No se ha podido eliminar el producto.");
    return;
  }
  resetForm();
  await refreshProducts(true);
}

async function refreshProducts(includeAll = state.adminUnlocked) {
  await loadTags();
  await loadProducts(includeAll);
  syncFilterOptions();
  renderProducts();
  if (state.adminUnlocked) renderAdminProducts();
}

function renderAdminTagInputs() {
  renderTypeSelect();
  renderCheckboxTags(els.colorsInput, "colors");
  renderCheckboxTags(els.groupsInput, "groups");
}

function renderTypeSelect() {
  const current = els.typeInput.value;
  els.typeInput.innerHTML = [
    `<option value="">Selecciona un tipo</option>`,
    ...state.tags.types.map((tag) => `<option value="${escapeHtml(tag)}">${escapeHtml(tag)}</option>`),
  ].join("");
  if (state.tags.types.includes(current)) els.typeInput.value = current;
}

function renderCheckboxTags(container, kind) {
  const selected = getCheckedTags(container);
  container.innerHTML = state.tags[kind]
    .map((tag) => {
      const checked = selected.includes(tag) ? "checked" : "";
      return `
        <label class="tag-choice">
          <input type="checkbox" value="${escapeHtml(tag)}" ${checked}>
          ${escapeHtml(tag)}
        </label>
      `;
    })
    .join("");
}

function getCheckedTags(container) {
  return Array.from(container.querySelectorAll("input:checked")).map((input) => input.value);
}

function setCheckedTags(container, tags) {
  const selected = new Set(tags);
  container.querySelectorAll("input").forEach((input) => {
    input.checked = selected.has(input.value);
  });
}

function renderTagManagerLists() {
  const labels = { types: "Tipos", colors: "Colores", groups: "Grupos" };
  els.tagManagerLists.innerHTML = Object.entries(labels)
    .map(([kind, label]) => {
      const tags = state.tags[kind].map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("");
      return `
        <section class="tag-list-panel">
          <h4>${label}</h4>
          <div class="tag-row">${tags || "<span class='empty-state'>Sin etiquetas</span>"}</div>
        </section>
      `;
    })
    .join("");
}

async function handleTagSubmit(event) {
  event.preventDefault();
  const response = await fetch("/api/tags", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify({
      kind: els.tagKindInput.value,
      name: els.tagNameInput.value.trim(),
    }),
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    alert(`No se ha podido crear la etiqueta. ${message}`);
    return;
  }

  els.tagNameInput.value = "";
  const data = await response.json();
  state.tags = data.tags;
  syncFilterOptions();
}

function adminHeaders() {
  return { "X-Admin-Password": state.adminPassword };
}

async function readErrorMessage(response) {
  try {
    const data = await response.json();
    return data.error || "";
  } catch {
    return "";
  }
}

function switchView(viewName) {
  document.querySelectorAll(".page-view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${viewName}`);
  });

  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.viewTarget === viewName);
  });

  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function init() {
  bindEvents();
  try {
    await refreshProducts(false);
  } catch {
    state.products = sampleProducts;
    syncFilterOptions();
    renderProducts();
  }
}

init();
