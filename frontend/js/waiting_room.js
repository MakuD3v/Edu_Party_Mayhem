import { socket } from './socket.js';
import loadingManager from './loading.js';

const urlParams = new URLSearchParams(window.location.search);
const sessionCode = urlParams.get('code');
const userId = localStorage.getItem('user_id');

if (!sessionCode || !userId) window.location.href = 'lobby.html';

document.getElementById('session-code-display').textContent = sessionCode;

// Fetch and display lobby name
async function fetchLobbyName() {
    try {
        const token = localStorage.getItem('access_token');
        const res = await fetch('/api/sessions/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const sessions = await res.json();
        const currentSession = sessions.find(s => s.session_code === sessionCode);

        if (currentSession) {
            // Auto-redirect if game is playing (fallback for missed WS event)
            if (currentSession.status === 'playing' || currentSession.status === 'active') {
                console.log('🔄 Game is playing! Redirecting...');
                window.location.href = `game.html?code=${sessionCode}`;
                return;
            }

            if (currentSession.lobby_name) {
                document.getElementById('lobby-name-display').textContent = currentSession.lobby_name;
            } else {
                document.getElementById('lobby-name-display').textContent = `CLASSROOM #${sessionCode}`;
            }
        }
    } catch (e) {
        console.error('Failed to fetch lobby name:', e);
        document.getElementById('lobby-name-display').textContent = `CLASSROOM #${sessionCode}`;
    }
}

fetchLobbyName();
// Poll every 3s to sync status/name
setInterval(fetchLobbyName, 3000);

// Elements
const teacherArea = document.getElementById('teacher-area');
const studentArea = document.getElementById('student-area');
const startBtn = document.getElementById('start-btn');
const readyBtn = document.getElementById('ready-btn');
const testBtn = document.getElementById('test-btn');

let isReady = false;

// Connect WS
socket.connect(sessionCode, userId);

// WS Events
socket.on('PLAYER_JOIN', (data) => console.log("Player join", data));

socket.on('PLAYER_LIST_UPDATE', (data) => {
    renderPlayers(data.players);
});

socket.on('GAME_START', (data) => {
    console.log('🚀 GAME_START received in waiting room! Redirecting...', data);
    window.location.href = `game.html?code=${sessionCode}`;
});

// Controls
document.getElementById('leave-btn').onclick = () => {
    window.location.href = 'lobby.html';
};

readyBtn.onclick = () => {
    isReady = !isReady;
    if (isReady) {
        readyBtn.textContent = "WAITING...";
        readyBtn.classList.remove('btn-green');
        readyBtn.style.background = '#f39c12';
    } else {
        readyBtn.textContent = "READY";
        readyBtn.classList.add('btn-green');
        readyBtn.style.background = '';
    }

    socket.send('PLAYER_READY', {
        is_ready: isReady,
        session_code: sessionCode,
        user_id: userId
    });
};

startBtn.onclick = () => {
    console.log('🔵 START button clicked!');
    loadingManager.show('Starting class...');

    if (socket.socket && socket.socket.readyState === WebSocket.OPEN) {
        console.log('📤 Socket OPEN, sending START_GAME...');
        socket.send('START_GAME', { session_code: sessionCode });
    } else {
        console.error('❌ Socket NOT OPEN in startBtn handler!', socket.socket ? socket.socket.readyState : 'null');
        alert("Connection lost! Please refresh the page.");
    }
};

testBtn.onclick = () => {
    console.log('🔵 TEST button clicked!');
    loadingManager.show('Starting test mode...');

    if (socket.socket && socket.socket.readyState === WebSocket.OPEN) {
        console.log('📤 Socket OPEN, sending START_GAME (test)...');
        socket.send('START_GAME', { session_code: sessionCode, force_test: true });
    } else {
        console.error('❌ Socket NOT OPEN in testBtn handler!', socket.socket ? socket.socket.readyState : 'null');
        alert("Connection lost! Please refresh the page.");
    }
};


// Render Helper
function renderPlayers(players) {
    teacherArea.innerHTML = '';
    studentArea.innerHTML = '';

    if (!players || players.length === 0) return;

    let hostFound = false;

    let allReady = true;
    let playerCount = 0;

    players.forEach(p => {
        playerCount++;
        if (!p.is_ready && !p.is_host) allReady = false; // Host ready doesn't matter as much or assumed ready

        const div = document.createElement('div');
        div.className = p.is_host ? 'teacher-podium' : 'student-avatar';

        const colors = ['#9b59b6', '#3498db', '#e67e22', '#e74c3c', '#1abc9c'];
        const color = p.is_host ? '#2c3e50' : colors[p.user_id % colors.length];

        // Host gets gold border via class 'host', students regular
        const boxClass = p.is_host ? 'avatar-box host' : 'avatar-box';

        div.innerHTML = `
            <div class="${boxClass}" style="background: ${color};">
                ${p.icon || '🎓'}
                ${p.is_ready ? '<div class="ready-badge">✓</div>' : ''}
            </div>
            <span style="font-family: var(--font-body); font-weight: bold; margin-top: 5px; color: ${p.is_host ? '#f1c40f' : 'white'};">
                ${p.name} ${p.is_host ? '(Teacher)' : ''}
            </span>
        `;

        if (p.is_host) {
            teacherArea.appendChild(div);
            hostFound = true;
            // Also if I am this host, show start button logic
            // Type-safe comparison: convert both to numbers
            const currentUserId = parseInt(userId);
            const playerUserId = parseInt(p.user_id);

            console.log(`Host check: currentUserId=${currentUserId}, playerUserId=${playerUserId}, isHost=${p.is_host}`);

            if (playerUserId === currentUserId) {
                console.log("✓ User is the host! Showing host controls.");

                // Show start and test buttons
                startBtn.classList.remove('hidden');
                startBtn.style.display = 'inline-block';

                testBtn.classList.remove('hidden');
                testBtn.style.display = 'inline-block';

                // Hide ready button
                readyBtn.classList.add('hidden');
                readyBtn.style.display = 'none';
            }
        } else {
            studentArea.appendChild(div);
        }
    });

    if (!hostFound) {
        teacherArea.innerHTML = '<p style="opacity:0.5;">Teacher is connecting...</p>';
    }

    // Host Button State
    if (!document.getElementById('start-btn').classList.contains('hidden')) {
        const canStart = (playerCount >= 2 && allReady);
        // Or if strictly testing, maybe relaxed? But requirement says "player amount met"

        if (canStart) {
            startBtn.disabled = false;
            startBtn.style.opacity = 1;
            startBtn.textContent = "START CLASS";
            startBtn.style.cursor = 'pointer';
        } else {
            startBtn.disabled = true;
            startBtn.style.opacity = 0.5;
            startBtn.textContent = playerCount < 2 ? "NEED MORE STUDENTS" : "WAITING FOR READY";
            startBtn.style.cursor = 'not-allowed';
        }
    }
}

// Initial Fetch - Wait for WebSocket to be ready
socket.onReady(() => {
    console.log('✓ WebSocket ready, requesting player list...');
    socket.send('GET_PLAYERS', { session_code: sessionCode });
});
