// UI Helpers
const ui = {
    form: document.getElementById('auth-form'),
    username: document.getElementById('username'),
    password: document.getElementById('password'),
    submitBtn: document.getElementById('submit-btn'),
    toggleBtn: document.getElementById('toggle-btn'),
    title: document.getElementById('form-title'),
    errorMsg: document.getElementById('error-msg'),
    loading: document.getElementById('loading-overlay')
};

let isLogin = true;

// Toggle Login/Register Mode
ui.toggleBtn.onclick = () => {
    isLogin = !isLogin;
    ui.title.textContent = isLogin ? 'Login' : 'Register';
    ui.submitBtn.textContent = isLogin ? 'Log In' : 'Register';
    ui.toggleBtn.textContent = isLogin ? 'Register' : 'Log In';
    ui.errorMsg.classList.add('hidden');
    ui.username.focus();
};

function showLoading() {
    ui.loading.classList.remove('hidden');
}

function hideLoading() {
    ui.loading.classList.add('hidden');
}

function showError(msg) {
    ui.errorMsg.textContent = msg;
    ui.errorMsg.classList.remove('hidden');
    ui.errorMsg.classList.add('shake-error');

    // Remove shake class after animation so it can be re-triggered
    setTimeout(() => {
        ui.errorMsg.classList.remove('shake-error');
    }, 500);
}

ui.form.onsubmit = async (e) => {
    e.preventDefault();
    const username = ui.username.value.trim();
    const password = ui.password.value.trim();

    if (!username || !password) {
        showError("Please fill in all fields");
        return;
    }

    showLoading();
    ui.errorMsg.classList.add('hidden');

    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            const data = await response.json();
            if (isLogin) {
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('user_id', data.user_id);
                localStorage.setItem('username', data.username || username); // Fallback
                window.location.href = 'lobby.html';
            } else {
                // Auto-login after register logic or switch to login view
                alert('Registered! Please login.'); // Keep simple alert for success -> switch
                ui.toggleBtn.click(); // Switch back to login
            }
        } else {
            const data = await response.json();
            showError(data.detail || 'Authentication failed');
        }
    } catch (err) {
        showError('Network error. Please try again.');
        console.error(err);
    } finally {
        hideLoading();
    }
};
