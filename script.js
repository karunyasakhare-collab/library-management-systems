"use strict";

const $ = (sel) => document.querySelector(sel);
const booksBody = $("#books-body");
const emptyMsg = $("#empty");
const searchBox = $("#search");
const membersList = $("#members-list");
const issueDialog = $("#issue-dialog");
const issueMember = $("#issue-member");
const toastEl = $("#toast");

let members = [];
let issuingBookId = null;
let toastTimer = null;

function toast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.className = "toast show" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3500);
}

async function api(path, options = {}) {
  const opts = { ...options };
  if (opts.body && typeof opts.body !== "string") {
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    opts.body = JSON.stringify(opts.body);
  }
  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new Error("Cannot reach the server. Is app.py running?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ").");
  return data;
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  children.forEach((c) => node.append(c));
  return node;
}

function actionButton(label, className, handler) {
  const b = el("button", { type: "button", textContent: label, className });
  b.addEventListener("click", handler);
  return b;
}

async function loadBooks() {
  try {
    const q = searchBox.value.trim();
    const books = await api("/api/books" + (q ? "?q=" + encodeURIComponent(q) : ""));
    renderBooks(books);
  } catch (e) {
    toast(e.message, true);
  }
}

function renderBooks(books) {
  booksBody.replaceChildren();
  emptyMsg.hidden = books.length > 0;
  for (const b of books) {
    const status = b.available
      ? el("span", { className: "badge in", textContent: "Available" })
      : el("span", { className: "badge out", textContent: "Issued to " + (b.issued_to || "a member") });
    const actions = el("div", { className: "actions" });
    if (b.available) {
      actions.append(actionButton("Issue", "", () => openIssue(b)));
    } else {
      actions.append(actionButton("Return", "ghost", () => returnBook(b.id)));
    }
    const del = actionButton("Delete", "danger", () => deleteBook(b));
    del.disabled = !b.available;
    del.title = b.available ? "" : "Return this book before deleting it";
    actions.append(del);

    const row = el("tr");
    [b.title, b.author, b.isbn, b.category].forEach((t) => row.append(el("td", { textContent: t })));
    row.append(el("td", {}, status), el("td", {}, actions));
    booksBody.append(row);
  }
}

async function loadMembers() {
  try {
    members = await api("/api/members");
    membersList.replaceChildren();
    for (const m of members) {
      membersList.append(el("li", { textContent: m.name }, el("small", { textContent: m.email })));
    }
    if (!members.length) membersList.append(el("li", { textContent: "No members yet. Add one above." }));
  } catch (e) {
    toast(e.message, true);
  }
}

function openIssue(book) {
  if (!members.length) {
    toast("Add a member before issuing a book.", true);
    return;
  }
  issuingBookId = book.id;
  $("#issue-title").textContent = book.title;
  issueMember.replaceChildren(
    ...members.map((m) => el("option", { value: m.id, textContent: m.name + " (" + m.email + ")" }))
  );
  issueDialog.showModal();
}

$("#issue-form").addEventListener("submit", async (ev) => {
  const action = ev.submitter ? ev.submitter.value : "cancel";
  if (action !== "ok") return;
  try {
    await api("/api/books/" + issuingBookId + "/issue", {
      method: "POST",
      body: { member_id: Number(issueMember.value) },
    });
    toast("Book issued.");
  } catch (e) {
    toast(e.message, true);
  }
  loadBooks();
});

async function returnBook(id) {
  try {
    await api("/api/books/" + id + "/return", { method: "POST" });
    toast("Book returned.");
  } catch (e) {
    toast(e.message, true);
  }
  loadBooks();
}

async function deleteBook(book) {
  if (!window.confirm('Delete "' + book.title + '"?')) return;
  try {
    await api("/api/books/" + book.id, { method: "DELETE" });
    toast("Book deleted.");
  } catch (e) {
    toast(e.message, true);
  }
  loadBooks();
}

$("#book-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const body = Object.fromEntries(new FormData(form));
  try {
    await api("/api/books", { method: "POST", body });
    form.reset();
    toast("Book added.");
    loadBooks();
  } catch (e) {
    toast(e.message, true);
  }
});

$("#member-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const body = Object.fromEntries(new FormData(form));
  try {
    await api("/api/members", { method: "POST", body });
    form.reset();
    toast("Member added.");
    loadMembers();
  } catch (e) {
    toast(e.message, true);
  }
});

let searchTimer = null;
searchBox.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadBooks, 200);
});

loadBooks();
loadMembers();
