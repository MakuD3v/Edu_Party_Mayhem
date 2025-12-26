import { socket } from './socket.js';
import { UI } from './ui.js';

const urlParams = new URLSearchParams(window.location.search);
const sessionCode = urlParams.get('code');
const userId = localStorage.getItem('user_id');

if (!sessionCode || !userId) window.location.href = 'lobby.html';

document.getElementById('game-title').textContent = `Session: ${sessionCode}`;

socket.connect(sessionCode, userId);

let currentGame = null;

// UI Elements
const views = {
    'Math Quiz': 'ui-math-quiz',
    'Speed Typing': 'ui-speed-typing',
    'Tech Sprint': 'ui-tech-sprint'
};

function hideAllViews() {
    Object.values(views).forEach(id => UI.hide(id));
    UI.hide('round-result');
}

socket.on('game_start', (data) => {
    hideAllViews();
    currentGame = data.game;
    document.getElementById('game-title').textContent = data.game;

    if (views[currentGame]) {
        UI.show(views[currentGame]);
    }

    if (currentGame === 'Math Quiz') {
        renderMathQuiz(data.questions);
    } else if (currentGame === 'Speed Typing') {
        renderSpeedTyping(data.word_list);
    } else if (currentGame === 'Tech Sprint') {
        renderTechSprint(data);
    }
});

socket.on('ACTION_RESULT', (data) => {
    // Feedback
    if (data.user_id == userId) {
        console.log("My Result:", data.result);
    }
});

socket.on('ROUND_END', (data) => {
    hideAllViews();
    UI.show('round-result');
    if (data.eliminated) {
        document.getElementById('round-msg').textContent = "You were eliminated!";
        setTimeout(() => window.location.href = 'lobby.html', 3000);
    } else {
        document.getElementById('round-msg').textContent = "You survived! Preparing next round...";
    }
});

socket.on('GAME_OVER', (data) => {
    // Navigate to results
    window.location.href = `results.html?code=${sessionCode}`;
});


// Mini-Game Logic

// Math Quiz
function renderMathQuiz(questions) {
    let qIdx = 0;
    const showQ = () => {
        if (qIdx >= questions.length) return;
        document.getElementById('math-question').textContent = questions[qIdx].text;
    };
    showQ();

    document.getElementById('math-submit').onclick = () => {
        const val = UI.getVal('math-answer');
        socket.send('GAME_ACTION', { action: { question_index: qIdx, answer: val } });
        qIdx++;
        UI.setVal('math-answer', '');
        if (qIdx < questions.length) showQ();
        else document.getElementById('math-question').textContent = "Done! Wait for others.";
    };
}

// Speed Typing
function renderSpeedTyping(words) {
    let wIdx = 0;
    document.getElementById('typing-word').textContent = words[0];

    document.getElementById('typing-answer').oninput = (e) => {
        if (e.target.value === words[wIdx]) {
            socket.send('GAME_ACTION', { action: { word: words[wIdx] } });
            wIdx++;
            e.target.value = '';
            if (wIdx < words.length) document.getElementById('typing-word').textContent = words[wIdx];
            else document.getElementById('typing-word').textContent = "Done!";
        }
    };
}

// Tech Sprint
function renderTechSprint(data) {
    let score = 0;
    document.getElementById('sprint-progress').textContent = `Score: 0 / ${data.target_score}`;
    document.getElementById('sprint-btn').onclick = () => {
        socket.send('GAME_ACTION', { action: { success: true } });
        score++; // Naive local update
        document.getElementById('sprint-progress').textContent = `Score: ${score}`;
    };
}
