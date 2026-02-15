class WordPortal {
    constructor() {
        this.isAdmin = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadGames();
        this.checkAuth();
    }

    bindEvents() {
        // Search
        document.getElementById('searchBtn').onclick = () => this.searchGames();
        document.getElementById('searchInput').onkeypress = (e) => {
            if (e.key === 'Enter') this.searchGames();
        };

        // Auth
        document.getElementById('loginBtn').onclick = () => this.showModal('loginModal');
        document.getElementById('registerBtn').onclick = () => this.showModal('registerModal');
        document.getElementById('logoutBtn').onclick = () => this.logout();

        // Forms
        document.getElementById('loginForm').onsubmit = (e) => {
            e.preventDefault();
            this.login();
        };
        document.getElementById('registerForm').onsubmit = (e) => {
            e.preventDefault();
            this.register();
        };
        document.getElementById('uploadForm').onsubmit = (e) => {
            e.preventDefault();
            this.uploadGame();
        };

        // Modal closes
        document.querySelectorAll('.close').forEach(close => {
            close.onclick = () => this.hideModal();
        });

        // Admin
        document.getElementById('adminBtn').onclick = () => {
            document.getElementById('adminPanel').style.display = 'block';
            document.getElementById('adminBtn').style.display = 'none';
        };
    }

    async api(endpoint, options = {}) {
        try {
            const response = await fetch(`/api${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            return await response.json();
        } catch (error) {
            this.showAlert('Ошибка соединения', 'error');
        }
    }

    async loadGames(search = '') {
        const gamesGrid = document.getElementById('gamesGrid');
        gamesGrid.innerHTML = '<div class="game-placeholder">Загрузка...</div>';

        const data = await this.api(`/games?search=${encodeURIComponent(search)}`);
        
        if (data.length === 0) {
            gamesGrid.innerHTML = '<div class="game-placeholder">Игр не найдено</div>';
            return;
        }

        gamesGrid.innerHTML = data.map(game => `
            <div class="game-card" data-game-id="${game.id}">
                ${game.avatar ? `<img src="/uploads/${game.avatar}" alt="${game.title}" class="game-avatar" onerror="this.style.display='none'">` : ''}
                <h3>${this.escapeHtml(game.title)}</h3>
                <p>${this.escapeHtml(game.description).substring(0, 150)}...</p>
                <div class="download-info">
                    <span>📥 ${game.downloads} скачиваний</span>
                    <a href="/download/${game.id}" class="download-btn" download>
                        Скачать игру
                    </a>
                </div>
            </div>
        `).join('');

        document.getElementById('gamesCount').textContent = data.length;
        document.getElementById('totalDownloads').textContent = data.reduce((sum, game) => sum + game.downloads, 0);
    }

    async checkAuth() {
        // Проверяем сессию через загрузку игр (если есть user info в localStorage)
        const userData = localStorage.getItem('wordUser');
        if (userData) {
            const user = JSON.parse(userData);
            this.showUserInfo(user.username, user.is_admin);
        }
    }

    showUserInfo(username, isAdmin) {
        this.isAdmin = isAdmin;
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('userInfo').style.display = 'flex';
        document.getElementById('userName').textContent = `👋 ${username}`;
        
        if (isAdmin) {
            document.getElementById('adminBtn').style.display = 'inline-block';
        }
    }

    async login() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        const result = await this.api('/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (result.success) {
            this.showUserInfo(result.username, result.is_admin);
            localStorage.setItem('wordUser', JSON.stringify({
                username: result.username,
                is_admin: result.is_admin
            }));
            this.hideModal();
            this.showAlert('✅ Вход успешен!');
            this.loadGames();
        } else {
            this.showAlert('❌ Неверный логин или пароль', 'error');
        }
    }

    async register() {
        const username = document.getElementById('regUsername').value;
        const password = document.getElementById('regPassword').value;

        const result = await this.api('/register', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (result.success) {
            this.showAlert('✅ Регистрация успешна! Теперь войдите');
            this.hideModal();
        } else {
            this.showAlert(`❌ ${result.error}`, 'error');
        }
    }

    async logout() {
        await this.api('/logout');
        localStorage.removeItem('wordUser');
        document.getElementById('authSection').style.display = 'flex';
        document.getElementById('userInfo').style.display = 'none';
        document.getElementById('adminPanel').style.display = 'none';
        this.showAlert('👋 Вы вышли из аккаунта');
        this.loadGames();
    }

    async uploadGame() {
        const formData = new FormData();
        formData.append('title', document.getElementById('gameTitle').value);
        formData.append('description', document.getElementById('gameDesc').value);
        formData.append('avatar', document.getElementById('gameAvatar').files[0] || '');
        formData.append('game_file', document.getElementById('gameFile').files[0]);

        const result = await fetch('/admin/upload', {
            method: 'POST',
            body: formData
        }).then(r => r.json());

        if (result.success) {
            this.showAlert('✅ Игра успешно загружена!');
            document.getElementById('uploadForm').reset();
            this.loadGames();
        } else {
            this.showAlert(`❌ ${result.error}`, 'error');
        }
    }

    searchGames() {
        const query = document.getElementById('searchInput').value;
        this.loadGames(query);
        document.getElementById('gamesTitle').textContent = `🔍 Результаты по: "${query}"`;
    }

    showModal(modalId) {
        document.getElementById(modalId).style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    hideModal() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
        document.body.style.overflow = 'auto';
    }

    showAlert(message, type = 'success') {
        const alerts = document.getElementById('alerts');
        const alert = document.createElement('div');
        alert.className = `alert ${type}`;
        alert.textContent = message;
        alerts.appendChild(alert);

        setTimeout(() => {
            alert.remove();
        }, 5000);
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize app
new WordPortal();
