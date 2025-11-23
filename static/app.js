const authOverlay = document.getElementById('auth-overlay');
const registerOverlay = document.getElementById('register-overlay');
const appRoot = document.getElementById('app');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const openRegister = document.getElementById('open-register');
const backToLogin = document.getElementById('back-to-login');
const usernameLabel = document.getElementById('username-label');

const defaultCategories = ['Amateur', 'Женское', 'Латинка', 'Жёсткое', 'Реальные', 'Новое', 'Студия', 'БДСМ', 'Curated'];
const defaultTags = ['Amateur', 'MILF', 'BDSM', 'Couple', 'BBC', 'Big ass', 'POV', 'Mobile', 'POV W'];
const defaultCreators = ['Создатель 1', 'Создатель 2', 'Создатель 3', 'Создатель 4', 'Создатель 5'];

function showLogin() {
  authOverlay.classList.add('active');
  registerOverlay.classList.remove('active');
}

function showRegister() {
  registerOverlay.classList.add('active');
  authOverlay.classList.remove('active');
}

function showApp() {
  authOverlay.classList.remove('active');
  registerOverlay.classList.remove('active');
  appRoot.hidden = false;
}

openRegister.addEventListener('click', showRegister);
backToLogin.addEventListener('click', showLogin);

async function api(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = options.headers || {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(path, { ...options, headers });
}

function renderChips(container, items, extraCountButtonId) {
  const el = document.getElementById(container);
  el.innerHTML = '';
  items.forEach((item) => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = item;
    el.appendChild(chip);
  });

  if (extraCountButtonId) {
    const button = document.getElementById(extraCountButtonId);
    button.onclick = () => {
      items.concat(items.slice(0, 3)).forEach((item) => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = item;
        el.appendChild(chip);
      });
    };
  }
}

function renderCreators(names) {
  const el = document.getElementById('creators');
  el.innerHTML = '';
  names.forEach((name) => {
    const card = document.createElement('div');
    card.className = 'creator-card';
    card.innerHTML = `<div class="creator-title">${name}</div><div class="creator-meta">12 роликов · 224 лайка</div><button class="primary" style="margin-top:8px;width:100%">Подписаться</button>`;
    el.appendChild(card);
  });
  document.getElementById('stat-creators').textContent = names.length;
}

async function loadCatalog() {
  try {
    const [categoriesRes, tagsRes] = await Promise.all([
      api('/categories'),
      api('/models'),
    ]);

    const categories = categoriesRes.ok ? (await categoriesRes.json()).map((c) => c.name) : defaultCategories;
    const tags = tagsRes.ok ? (await tagsRes.json()).map((t) => t.name) : defaultTags;

    renderChips('categories', categories, 'show-more-categories');
    renderChips('tags', tags, 'show-more-tags');
  } catch (e) {
    renderChips('categories', defaultCategories);
    renderChips('tags', defaultTags);
  }

  renderCreators(defaultCreators);
  document.getElementById('stat-videos').textContent = '1827';
  document.getElementById('stat-members').textContent = '6540';
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const body = new URLSearchParams();
  body.append('username', formData.get('username'));
  body.append('password', formData.get('password'));

  const response = await api('/auth/login', {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  if (!response.ok) {
    alert('Не удалось войти. Проверьте логин/пароль.');
    return;
  }

  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  await afterAuth();
}

async function handleRegister(event) {
  event.preventDefault();
  const formData = new FormData(registerForm);
  const payload = {
    username: formData.get('username'),
    email: formData.get('email'),
    password: formData.get('password'),
  };

  const response = await api('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    alert('Не удалось зарегистрироваться. Возможно, логин или email уже заняты.');
    return;
  }

  alert('Аккаунт создан! Теперь войдите в систему.');
  showLogin();
}

async function afterAuth() {
  showApp();
  await loadCatalog();
  try {
    const res = await api('/me');
    if (res.ok) {
      const user = await res.json();
      usernameLabel.textContent = user.username;
    }
  } catch (e) {}
}

loginForm.addEventListener('submit', handleLogin);
registerForm.addEventListener('submit', handleRegister);

document.addEventListener('DOMContentLoaded', async () => {
  const token = localStorage.getItem('token');
  if (token) {
    await afterAuth();
  } else {
    showLogin();
  }
});
