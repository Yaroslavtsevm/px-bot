const API_URL = 'https://твой-backend.onrender.com'; // ← замени после деплоя
let currentLang = localStorage.getItem('lang') || 'ru';
let currentTab = 0;
let allModels = [];

const tg = Telegram.WebApp;
tg.ready();
tg.expand();

const user = tg.initDataUnsafe.user;
if (user && String(user.id) === '1423028519') {
  document.getElementById('admin-btn').classList.remove('hidden');
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('lang', lang);
  document.getElementById('btn-ru').classList.toggle('bg-pink-600', lang === 'ru');
  document.getElementById('btn-en').classList.toggle('bg-pink-600', lang === 'en');
  loadData();
}

async function loadData() {
  const res = await fetch(`${API_URL}/api/models`);
  allModels = await res.json();
  renderModels();
  if (currentTab === 1) loadHashtags();
}

function renderModels(filtered = null) {
  const models = filtered || allModels;
  const grid = document.getElementById('models-grid');
  grid.innerHTML = '';
  models.forEach(m => {
    const name = currentLang === 'ru' ? m.name_ru : m.name_en || m.name_ru;
    const card = document.createElement('div');
    card.className = 'card bg-zinc-900 rounded-3xl overflow-hidden cursor-pointer';
    card.innerHTML = `<img src="${m.photo_url}" class="w-full aspect-square object-cover"><div class="p-4 text-center font-semibold">${name}</div>`;
    card.onclick = () => loadModelVideos(m._id, name);
    grid.appendChild(card);
  });
}

async function loadModelVideos(modelId, title) {
  const res = await fetch(`${API_URL}/api/videos/model/${modelId}`);
  const videos = await res.json();
  showVideoModal(videos, title);
}

async function loadHashtags() {
  const res = await fetch(`${API_URL}/api/hashtags`);
  const tags = await res.json();
  const container = document.getElementById('hashtags');
  container.innerHTML = tags.map(tag => `<button onclick="loadVideosByTag('${tag}')" class="bg-zinc-800 hover:bg-pink-900 px-6 py-3 rounded-2xl text-lg">${tag}</button>`).join('');
}

async function loadVideosByTag(tag) {
  const res = await fetch(`${API_URL}/api/videos/hashtag/${encodeURIComponent(tag)}`);
  const videos = await res.json();
  showVideoModal(videos, tag);
}

function showVideoModal(videos, title) {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black/95 z-[200] overflow-auto p-4';
  let html = `<div class="max-w-5xl mx-auto"><div class="flex justify-between sticky top-0 bg-black py-4"><h2 class="text-4xl">${title}</h2><button onclick="this.closest('.fixed').remove()" class="text-5xl">✕</button></div><div class="space-y-16">`;

  videos.forEach(v => {
    const titleText = currentLang === 'ru' ? v.title_ru : v.title_en;
    const desc = currentLang === 'ru' ? v.description_ru : v.description_en;
    html += `
      <div>
        <h3 class="text-2xl mb-4">${titleText}</h3>
        <div id="player-${v._id}" class="cld-video-player" data-cld-public-id="${v.video_url.split('/').pop().split('.')[0]}" style="height: 500px;"></div>
        <p class="mt-4 text-zinc-400">${desc || ''}</p>
      </div>`;
  });
  html += `</div></div>`;
  modal.innerHTML = html;
  document.body.appendChild(modal);

  // Инициализация Cloudinary Video Player с HLS
  setTimeout(() => {
    videos.forEach(v => {
      const player = cloudinary.videoPlayer(`player-${v._id}`, {
        cloud_name: 'твой_cloud_name',   // ← замени на свой Cloudinary cloud_name
        fluid: true,
        controls: true,
        muted: false
      });
      player.source(v.video_url.split('/').pop().split('.')[0], {
        sourceTypes: ['hls'],
        transformation: { streaming_profile: 'full_hd' }
      });
    });
  }, 500);
}

function search() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return renderModels();
  fetch(`${API_URL}/api/search?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => renderModels(data.models));
}

// Админ панель
function toggleAdminPanel() {
  const panel = document.getElementById('admin-panel');
  panel.classList.toggle('hidden');
  if (!panel.classList.contains('hidden')) loadAdminLists();
}

async function loadAdminLists() {
  const modelsRes = await fetch(`${API_URL}/api/models`);
  const models = await modelsRes.json();
  const videosRes = await fetch(`${API_URL}/api/videos/model/0`); // костыль — лучше сделать отдельный /api/videos/all
  const videos = await videosRes.json(); // временно

  let html = `<h3 class="text-2xl mb-6">Модели</h3><div class="grid grid-cols-3 gap-4 mb-12">`;
  models.forEach(m => {
    html += `<div class="bg-zinc-800 p-4 rounded-2xl"><img src="${m.photo_url}" class="w-full h-40 object-cover rounded-xl mb-3"><p>${m.name_ru}</p><button onclick="deleteModel('${m._id}')" class="text-red-500 text-sm mt-2">Удалить</button></div>`;
  });
  html += `</div>`;

  // Аналогично для видео (сокращённо)
  document.getElementById('admin-lists').innerHTML = html + `<h3 class="text-2xl mb-4">Видео (удаление через модалку видео)</h3>`;
}

async function addModel() {
  const form = new FormData();
  form.append('name_ru', document.getElementById('model-ru').value);
  form.append('name_en', document.getElementById('model-en').value);
  form.append('photo', document.getElementById('model-photo').files[0]);
  form.append('user', JSON.stringify(user));

  await fetch(`${API_URL}/api/admin/model`, { method: 'POST', body: form });
  alert('Модель добавлена');
  loadData();
}

async function addVideo() {
  const form = new FormData();
  form.append('title_ru', document.getElementById('video-title-ru').value);
  form.append('title_en', document.getElementById('video-title-en').value);
  form.append('description_ru', document.getElementById('video-desc-ru').value);
  form.append('description_en', document.getElementById('video-desc-en').value);
  form.append('modelIds', Array.from(document.getElementById('video-models').selectedOptions).map(o => o.value).join(','));
  form.append('hashtags', document.getElementById('video-hashtags').value);
  form.append('video', document.getElementById('video-file').files[0]);
  form.append('user', JSON.stringify(user));

  await fetch(`${API_URL}/api/admin/video`, { method: 'POST', body: form });
  alert('Видео добавлено');
  loadData();
}

async function deleteModel(id) {
  if (confirm('Удалить модель?')) {
    await fetch(`${API_URL}/api/admin/model/${id}`, { method: 'DELETE', body: JSON.stringify({ user: JSON.stringify(user) }) });
    loadData();
  }
}

async function showDonate() {
  const amount = prompt('Введите сумму Stars (50, 100, 250 и т.д.)', '100');
  if (!amount) return;
  const res = await fetch(`${API_URL}/api/create-invoice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount, user: JSON.stringify(user) })
  });
  const { invoice_link } = await res.json();
  tg.openInvoice(invoice_link);
}

// Инициализация
switchTab(0);
loadData();
setLang(currentLang);
