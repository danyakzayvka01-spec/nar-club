/* Адрес API задается в config.js перед публикацией. */
const API_BASE = window.APP_CONFIG?.apiBase || "";
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }
const state = { menu: [], category: "", quantities: new Map(), busy: false };
const els = Object.fromEntries(["table","tabs","products","category-title","item-count","submit","total","notice","greeting","toast"].map(id => [id, document.getElementById(id)]));
const rubles = n => `${new Intl.NumberFormat("ru-RU").format(n)} ₽`;
function showNotice(message, error=false) { els.notice.textContent=message; els.notice.classList.toggle("error",error); els.notice.classList.remove("hidden"); }
function hideNotice() { els.notice.classList.add("hidden"); }
function setQty(id, delta) { const next=Math.max(0,(state.quantities.get(id)||0)+delta); next?state.quantities.set(id,next):state.quantities.delete(id); renderProducts(); renderTotal(); }
function renderTabs() {
  const categories=[...new Set(state.menu.map(p=>p.category))];
  if (!state.category && categories.length) state.category=categories[0];
  els.tabs.replaceChildren(...categories.map(category=>{const b=document.createElement("button");b.className=`tab ${category===state.category?"active":""}`;b.textContent=category;b.onclick=()=>{state.category=category;renderTabs();renderProducts();};return b;}));
  els["category-title"].textContent=state.category||"Меню";
}
function renderProducts() {
  const products=state.menu.filter(p=>p.category===state.category);els["item-count"].textContent=`${products.length} позиций`;
  if (!products.length) { els.products.innerHTML='<div class="empty">В этой категории пока нет позиций</div>';return; }
  els.products.replaceChildren(...products.map(product=>{
    const card=document.createElement("article");card.className="product";
    const info=document.createElement("div");info.className="product-info";
    const name=document.createElement("div");name.className="product-name";name.textContent=product.name;
    const price=document.createElement("div");price.className="product-price";price.textContent=rubles(product.price);
    info.append(name,price);
    const counter=document.createElement("div");counter.className="counter";
    const minus=document.createElement("button");minus.type="button";minus.setAttribute("aria-label",`Уменьшить ${product.name}`);minus.textContent="−";minus.onclick=()=>setQty(product.id,-1);
    const qty=document.createElement("span");qty.className="qty";qty.textContent=state.quantities.get(product.id)||0;
    const plus=document.createElement("button");plus.type="button";plus.className="plus";plus.setAttribute("aria-label",`Добавить ${product.name}`);plus.textContent="+";plus.onclick=()=>setQty(product.id,1);
    counter.append(minus,qty,plus);card.append(info,counter);return card;
  }));
}
function renderTotal() {
  const total=state.menu.reduce((sum,p)=>sum+p.price*(state.quantities.get(p.id)||0),0);
  els.total.textContent=rubles(total);els.submit.disabled=state.busy||total===0||!els.table.value;
}
async function loadMenu() {
  if (!API_BASE) { showNotice("Укажите адрес backend API в config.js после развертывания.",true);return; }
  try {
    const response=await fetch(`${API_BASE}/api/menu`);if(!response.ok)throw new Error("Не удалось загрузить меню");
    state.menu=await response.json();renderTabs();renderProducts();renderTotal();hideNotice();
  } catch(error) { showNotice(`${error.message}. Проверьте подключение к интернету.`,true); }
}
async function submitOrder() {
  if (state.busy) return;
  const initData=tg?.initData||"";
  if (!initData) { showNotice("Откройте приложение через Telegram-бота. В обычном браузере заказ недоступен.",true);return; }
  const items=[...state.quantities].filter(([,quantity])=>quantity>0).map(([product_id,quantity])=>({product_id,quantity}));
  if (!items.length||!els.table.value) return;
  state.busy=true;els.submit.querySelector("span").textContent="Отправляем…";renderTotal();hideNotice();
  try {
    const response=await fetch(`${API_BASE}/api/orders`,{method:"POST",headers:{"Content-Type":"application/json","Authorization":`tma ${initData}`},body:JSON.stringify({table:Number(els.table.value),items})});
    const result=await response.json();if(!response.ok)throw new Error(result.detail||"Не удалось отправить заказ");
    state.quantities.clear();els.table.value="";renderProducts();renderTotal();showNotice(`Заказ №${result.order_id} принят и отправлен персоналу.`);tg?.HapticFeedback?.notificationOccurred("success");
  } catch(error) { showNotice(error.message,true);tg?.HapticFeedback?.notificationOccurred("error"); }
  finally {state.busy=false;els.submit.querySelector("span").textContent="Оформить заказ";renderTotal();}
}
async function init() {
  const user=tg?.initDataUnsafe?.user; if(user) els.greeting.textContent=`Официант: ${[user.first_name,user.last_name].filter(Boolean).join(" ")}`;
  try {const response=await fetch(`${API_BASE}/api/config`);if(response.ok){const config=await response.json();for(let table=1;table<=config.table_count;table++){const option=document.createElement("option");option.value=table;option.textContent=`Стол №${table}`;els.table.append(option);}}}catch{}
  els.table.addEventListener("change",renderTotal);els.submit.addEventListener("click",submitOrder);await loadMenu();
}
init();
