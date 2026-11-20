// 食事の記録の画面。今ある API（/foods・/meals・/summary）を呼ぶだけ。
"use strict";

const MEAL_TYPES = ["朝食", "昼食", "夕食", "間食"];

const $ = (id) => document.getElementById(id);

const state = {
  selectedFood: null, // 候補から選んだ食品 {id, name, ...}
  cart: [],           // [{food_id, name, grams}]
  searchSeq: 0,       // 古い検索結果で上書きしないための番号
};

// ---------- 共通 ----------

// 今日の日付（端末の時刻で）を YYYY-MM-DD にする
function today() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// 栄養の値を小数1桁に丸めて表示する（NULL は「-」）
function fmt(value) {
  return value === null || value === undefined ? "-" : (Math.round(value * 10) / 10).toFixed(1);
}

// API を呼ぶ。失敗したら、表示用のメッセージを持った Error を投げる
async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, options);
  } catch (e) {
    throw new Error("サーバーにつながりません");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(`エラー（${res.status}）\n${errorText(data)}`);
  }
  return data;
}

// FastAPI のエラー（detail が文字列か、項目ごとのリスト）を読める文にする
function errorText(data) {
  if (!data || data.detail === undefined) return "";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((d) => `${(d.loc || []).filter((x) => x !== "body").join(".")}: ${d.msg}`)
      .join("\n");
  }
  return JSON.stringify(data.detail);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text; // textContent なので HTML として解釈されない
  return node;
}

function showError(node, message) {
  node.textContent = message;
  node.hidden = !message;
}

// ---------- 検索 ----------

let searchTimer = null;

function onKeywordInput() {
  clearTimeout(searchTimer);
  // 打つたびに呼ばないよう、少し待ってから検索する
  searchTimer = setTimeout(searchFoods, 300);
}

async function searchFoods() {
  const keyword = $("keyword").value.trim();
  const seq = ++state.searchSeq;
  const list = $("candidates");

  if (!keyword) {
    list.replaceChildren();
    $("search-message").textContent = "";
    return;
  }

  let foods;
  try {
    foods = await api("GET", `/foods?keyword=${encodeURIComponent(keyword)}`);
  } catch (e) {
    if (seq !== state.searchSeq) return;
    list.replaceChildren();
    $("search-message").textContent = e.message;
    return;
  }
  if (seq !== state.searchSeq) return; // もっと新しい検索が走っている

  list.replaceChildren();
  $("search-message").textContent = foods.length === 0 ? "見つかりませんでした" : "";
  for (const food of foods) {
    const li = el("li");
    const btn = el("button");
    btn.type = "button";
    btn.append(
      el("span", "", food.name),
      el("span", "sub", `100gあたり ${fmt(food.calories)}kcal / P ${fmt(food.protein)} F ${fmt(food.fat)} C ${fmt(food.carbs)}`)
    );
    if (state.selectedFood && state.selectedFood.id === food.id) btn.classList.add("active");
    btn.addEventListener("click", () => selectFood(food, btn));
    li.append(btn);
    list.append(li);
  }
}

function selectFood(food, btn) {
  state.selectedFood = food;
  for (const b of $("candidates").querySelectorAll("button")) b.classList.remove("active");
  btn.classList.add("active");
  $("selected-name").textContent = food.name;
  $("selected").hidden = false;
  $("grams").focus();
}

// ---------- かご ----------

function addToCart() {
  const food = state.selectedFood;
  if (!food) return;
  const grams = Number($("grams").value);
  if (!$("grams").value || !Number.isFinite(grams) || grams <= 0) {
    alert("グラムは 0 より大きい数を入れてください");
    return;
  }
  state.cart.push({ food_id: food.id, name: food.name, grams });
  $("grams").value = "";
  renderCart();
}

function renderCart() {
  const list = $("cart");
  list.replaceChildren();
  state.cart.forEach((item, index) => {
    const li = el("li");
    const main = el("div", "main");
    main.append(el("span", "", item.name), el("span", "sub", `${item.grams} g`));
    const remove = el("button", "danger", "取り消す");
    remove.type = "button";
    remove.addEventListener("click", () => {
      state.cart.splice(index, 1);
      renderCart();
    });
    li.append(main, remove);
    list.append(li);
  });
  $("cart-empty").hidden = state.cart.length > 0;
  $("submit").disabled = state.cart.length === 0;
}

async function submitCart() {
  if (state.cart.length === 0) return;
  const body = {
    date: $("date").value,
    meal_type: $("meal-type").value,
    items: state.cart.map(({ food_id, grams }) => ({ food_id, grams })),
  };
  $("submit").disabled = true; // 二度押しで2回記録しないように
  try {
    await api("POST", "/meals", body);
  } catch (e) {
    // 失敗したら、エラーを表示し、かごは残す
    showError($("post-error"), e.message);
    $("submit").disabled = false;
    return;
  }
  showError($("post-error"), "");
  state.cart = [];
  renderCart();
  await loadDay();
}

// ---------- その日の合計・一覧 ----------

async function loadDay() {
  const date = $("date").value;
  if (!date) return;
  showError($("load-error"), "");
  try {
    const [summary, meals] = await Promise.all([
      api("GET", `/summary?date=${encodeURIComponent(date)}`),
      api("GET", `/meals?date=${encodeURIComponent(date)}`),
    ]);
    if (date !== $("date").value) return; // 読み込み中に日付が変わった
    renderSummary(summary);
    renderMeals(meals);
  } catch (e) {
    showError($("load-error"), e.message);
  }
}

function renderSummary(summary) {
  const total = summary.nutrition.total;
  $("total-calories").textContent = fmt(total.calories);
  $("total-protein").textContent = fmt(total.protein);
  $("total-fat").textContent = fmt(total.fat);
  $("total-carbs").textContent = fmt(total.carbs);

  // 未測定（NULL）の品があれば、合計に入っていないことを知らせる
  const labels = { calories: "カロリー", protein: "たんぱく質", fat: "脂質", carbs: "炭水化物" };
  const missing = Object.entries(summary.nutrition.missing)
    .filter(([, n]) => n > 0)
    .map(([key, n]) => `${labels[key]} ${n}品`);
  const note = $("missing-note");
  note.textContent = missing.length ? `未測定で合計に入っていないもの：${missing.join("、")}` : "";
  note.hidden = missing.length === 0;
}

function renderMeals(meals) {
  const box = $("meals");
  box.replaceChildren();
  $("meals-empty").hidden = meals.length > 0;

  // 区分ごとにまとめて表示する（区分の中は記録した順）
  for (const type of MEAL_TYPES) {
    const rows = meals.filter((m) => m.meal_type === type);
    if (rows.length === 0) continue;
    const group = el("div", "meal-group");
    group.append(el("h3", "", type));
    const list = el("ul", "list");
    for (const meal of rows) {
      const li = el("li");
      const main = el("div", "main");
      main.append(
        el("span", "", meal.food_name),
        el("span", "sub",
          `${meal.grams} g ・ ${fmt(meal.calories)}kcal / P ${fmt(meal.protein)} F ${fmt(meal.fat)} C ${fmt(meal.carbs)}`)
      );
      const del = el("button", "danger", "削除");
      del.type = "button";
      del.addEventListener("click", () => deleteMeal(meal, del));
      li.append(main, del);
      list.append(li);
    }
    group.append(list);
    box.append(group);
  }
}

async function deleteMeal(meal, button) {
  if (!confirm(`「${meal.food_name}」を削除しますか？`)) return;
  button.disabled = true;
  try {
    await api("DELETE", `/meals/${meal.id}`);
  } catch (e) {
    showError($("load-error"), e.message);
    button.disabled = false;
    return;
  }
  await loadDay();
}

// ---------- 起動 ----------

$("date").value = today();
$("keyword").addEventListener("input", onKeywordInput);
$("add-to-cart").addEventListener("click", addToCart);
$("grams").addEventListener("keydown", (e) => {
  if (e.key === "Enter") addToCart();
});
$("submit").addEventListener("click", submitCart);
$("date").addEventListener("change", loadDay);

renderCart();
loadDay();
