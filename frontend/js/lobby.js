import loadingManager from './loading.js';

// Elements
const slider = document.getElementById('player-count');
const sliderDisplay = document.getElementById('player-count-display');
const createBtn = document.getElementById('create-session-btn');
const joinBtn = document.getElementById('join-code-btn');

// Profile Elements
const profileTrigger = document.getElementById('profile-trigger');
const profileModal = document.getElementById('profile-modal');
const closeProfileBtn = document.getElementById('close-profile-btn');
const editNameInput = document.getElementById('edit-name');
const profileNameDisplay = document.getElementById('user-name-display');
const userAvatarSmall = document.getElementById('user-avatar-small');

// Data
const userId = localStorage.getItem('user_id');
const token = localStorage.getItem('access_token');

if (!token) window.location.href = 'index.html';

// State
let currentProfile = {
    name: localStorage.getItem('username') || 'Student',
    icon: '🎓'
};

// Init
function init() {
    profileNameDisplay.textContent = currentProfile.name;
    editNameInput.value = currentProfile.name;
    userAvatarSmall.textContent = currentProfile.icon;
    loadSessions();
    setInterval(loadSessions, 5000);
}

// Slider Logic
if (slider) {
    slider.oninput = (e) => {
        sliderDisplay.textContent = e.target.value;
    };
}

// Session Logic
createBtn.onclick = async () => {
    const players = parseInt(slider.value);
    const isPublic = true; // Default public for theme
    const lobbyName = document.getElementById('lobby-name')?.value.trim() || null;

    if (!userId) return window.location.href = 'index.html';

    const loader = await loadingManager.showMinimum('Creating class...');

    try {
        const response = await fetch('/api/sessions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                host_id: parseInt(userId),
                max_players: players,
                is_public: isPublic,
                lobby_name: lobbyName
            })
        });

        if (response.ok) {
            const session = await response.json();
            loadingManager.updateMessage('Entering waiting room...');
            await new Promise(resolve => setTimeout(resolve, 300));
            window.location.href = `waiting_room.html?code=${session.session_code}`;
        } else {
            await loader.hide();
            alert('Failed to create session');
        }
    } catch (e) {
        console.error(e);
        await loader.hide();
        alert('Network error');
    }
};

joinBtn.onclick = async () => {
    const code = document.getElementById('join-code').value.trim();
    if (code) await joinSession(code);
};

// Profile Logic
profileTrigger.onclick = () => {
    profileModal.classList.remove('hidden');
};

closeProfileBtn.onclick = async () => {
    profileModal.classList.add('hidden');
    await saveProfile();
};

// Icon Selection Global Helper Bridge
window.selectIcon = (icon) => {
    currentProfile.icon = icon;
    userAvatarSmall.textContent = icon;
    showToast();
};

// Name Auto-Save (Debounced)
let timeout = null;
editNameInput.oninput = (e) => {
    currentProfile.name = e.target.value;
    profileNameDisplay.textContent = currentProfile.name;

    clearTimeout(timeout);
    timeout = setTimeout(saveProfile, 1000);
};

async function saveProfile() {
    localStorage.setItem('username', currentProfile.name);
    // Persist to API
    try {
        await fetch(`/api/profile/${userId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ display_name: currentProfile.name })
        });
        showToast();
    } catch (e) { console.error(e); }
}

function showToast() {
    const toast = document.getElementById('toast');
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 2000);
}

// Session List
async function joinSession(code) {
    const loader = await loadingManager.showMinimum('Joining class...');

    try {
        const res = await fetch(`/api/sessions/${code}/join?user_id=${userId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            loadingManager.updateMessage('Entering waiting room...');
            await new Promise(resolve => setTimeout(resolve, 300));
            window.location.href = `waiting_room.html?code=${code}`;
        } else {
            await loader.hide();
            alert("Found no session or session full");
        }
    } catch (e) {
        console.error(e);
        await loader.hide();
        alert("Join failed");
    }
}

async function loadSessions() {
    const list = document.getElementById('session-list');
    try {
        const res = await fetch('/api/sessions/', { headers: { 'Authorization': `Bearer ${token}` } });
        const sessions = await res.json();

        list.innerHTML = '';
        if (sessions.length === 0) {
            list.innerHTML = '<p style="font-family: \'Sniglet\'; opacity:0.8;">No active classes. Be the first!</p>';
            return;
        }

        sessions.forEach(s => {
            const item = document.createElement('div');
            // Style as a line item on the chalkboard
            item.style.width = '100%';
            item.style.padding = '10px';
            item.style.borderBottom = '2px dashed rgba(255,255,255,0.3)';
            item.style.cursor = 'pointer';
            item.style.display = 'flex';
            item.style.justifyContent = 'space-between';
            item.style.alignItems = 'center';

            // Display lobby name if available, otherwise use session code
            const displayName = s.lobby_name || `Class #${s.session_code}`;

            item.innerHTML = `
                <div style="font-family: var(--font-heading); font-size: 1.2em;">${displayName}</div>
                <div style="background: rgba(0,0,0,0.3); padding: 5px 10px; border-radius: 10px;">${s.max_players} Slots</div>
            `;
            item.onclick = () => {
                document.getElementById('join-code').value = s.session_code;
                joinSession(s.session_code);
            }
            list.appendChild(item);
        });
    } catch (e) {
        console.error(e);
    }
}

init();
