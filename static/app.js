const STORAGE_KEY = "test_ninja_todos";

/** @type {{ id: string, text: string, done: boolean }[]} */
let todos = loadTodos();

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const list = document.getElementById("todo-list");
const countEl = document.getElementById("todo-count");
const clearBtn = document.getElementById("clear-completed");
const buildInfo = document.getElementById("build-info");
const filterButtons = document.querySelectorAll(".filter-btn");

/** @type {"all" | "active" | "done"} */
let filter = "all";

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    filter = btn.dataset.filter;
    filterButtons.forEach((b) => b.classList.toggle("active", b === btn));
    render();
  });
});

fetch("/health")
  .then((r) => r.json())
  .then((data) => {
    if (data.version) {
      buildInfo.textContent = `Live app version ${data.version} (from deploy callback)`;
    }
  })
  .catch(() => {
    buildInfo.textContent = "";
  });

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  todos.push({ id: crypto.randomUUID(), text, done: false });
  input.value = "";
  saveAndRender();
});

clearBtn.addEventListener("click", () => {
  todos = todos.filter((t) => !t.done);
  saveAndRender();
});

function loadTodos() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveAndRender() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  render();
}

function visibleTodos() {
  if (filter === "active") return todos.filter((t) => !t.done);
  if (filter === "done") return todos.filter((t) => t.done);
  return todos;
}

function render() {
  list.innerHTML = "";
  const shown = visibleTodos();
  if (todos.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No todos yet — add one above.";
    list.appendChild(li);
  } else if (shown.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "Nothing in this filter — try another tab.";
    list.appendChild(li);
  } else {
    for (const todo of shown) {
      list.appendChild(createItem(todo));
    }
  }
  const active = todos.filter((t) => !t.done).length;
  countEl.textContent =
    active === 1 ? "1 item left" : `${active} items left`;
}

function createItem(todo) {
  const li = document.createElement("li");
  li.className = "todo-item" + (todo.done ? " done" : "");

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = todo.done;
  checkbox.addEventListener("change", () => {
    todo.done = checkbox.checked;
    saveAndRender();
  });

  const label = document.createElement("label");
  label.textContent = todo.text;

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove";
  remove.setAttribute("aria-label", "Remove todo");
  remove.textContent = "×";
  remove.addEventListener("click", () => {
    todos = todos.filter((t) => t.id !== todo.id);
    saveAndRender();
  });

  li.append(checkbox, label, remove);
  return li;
}

render();
