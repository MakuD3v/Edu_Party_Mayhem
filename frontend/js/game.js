import { socket } from './socket.js';
import loadingManager from './loading.js';

console.log('🎮 Game.js loaded');

const urlParams = new URLSearchParams(window.location.search);
const sessionCode = urlParams.get('code');
const userId = localStorage.getItem('user_id');

console.log(`Session Code: ${sessionCode}, User ID: ${userId}`);

if (!sessionCode || !userId) window.location.href = 'lobby.html';

// Elements
const stages = {
    intro: document.getElementById('stage-intro'),
    tutorial: document.getElementById('stage-tutorial'),
    countdown: document.getElementById('stage-countdown'),
    game: document.getElementById('stage-game'),
    intermission: document.getElementById('stage-intermission')
};

// Mode Containers
const modes = {
    quiz: document.getElementById('game-mode-quiz'),
    typing: document.getElementById('game-mode-typing'),
    syntax: document.getElementById('game-mode-syntax'),
    math: document.getElementById('game-mode-math'),
    tf: document.getElementById('game-mode-tf')
};

// State
let currentQuestionIndex = 0;
let questions = []; // or snippets/words
let currentMode = 'quiz';
let myScore = 0;
let gameActive = false;

class GameFlow {
    static showStage(stageName) {
        Object.values(stages).forEach(el => el.classList.remove('active-stage'));
        stages[stageName].classList.add('active-stage');
    }

    static async startSequence(data) {
        currentMode = data.game_type || 'quiz';
        console.log(`🎮 Starting game mode: ${currentMode}`);

        // Force hide loading overlay in case it's still showing
        loadingManager.hide();

        // 1. INTRO
        this.updateIntro(data);
        this.showStage('intro');
        await this.wait(3000);

        // 2. TUTORIAL
        this.updateTutorial(data);
        this.showStage('tutorial');
        await this.runTimer('tut-timer', 5);

        // 3. COUNTDOWN
        // Explicitly hide tutorial before showing countdown
        stages.tutorial.classList.remove('active-stage');
        this.showStage('countdown');
        await this.runCountdown();

        // 4. GAME
        gameActive = true;
        this.startGame(data);

        // 5. TIMER / WIN CHECK
        if (data.time_limit) {
            // Time-based game (Math, Typing, Syntax)
            await this.runGameTimer(data.time_limit);
            if (gameActive) this.finishGame();
        } else {
            // Goal-based game (Race, TF) - waits for score logic to call finishGame
            document.getElementById('game-timer').textContent = "RACE!";
        }
    }

    static updateIntro(data) {
        document.getElementById('intro-title').textContent = data.game_title;
        document.getElementById('intro-icon').textContent = data.game_icon;
    }

    static updateTutorial(data) {
        document.getElementById('tut-title').textContent = data.game_title;
        document.getElementById('tut-icon').textContent = data.game_icon;
        document.getElementById('tut-desc').textContent = data.tutorial.text;

        const list = document.getElementById('tut-rules');
        list.innerHTML = data.tutorial.rules.map(r => `<li>${r}</li>`).join('');
    }

    static async runCountdown() {
        const el = document.getElementById('countdown-number');
        for (let i = 3; i > 0; i--) {
            el.textContent = i;
            await this.wait(1000);
        }
        el.textContent = "GO!";
        await this.wait(500);
    }

    static startGame(data) {
        this.showStage('game');
        document.getElementById('game-title-main').textContent = data.game_title;

        // CLEANUP: Remove old qualification overlay if exists (fix for persisting overlay)
        const oldOverlay = document.getElementById('qualified-overlay');
        if (oldOverlay) oldOverlay.remove();

        // Show Slots Available
        const slotsObj = data.slots_available || 1;
        const slotsText = document.getElementById('slots-display') || document.createElement('div');
        if (!document.getElementById('slots-display')) {
            slotsText.id = 'slots-display';
            slotsText.style.position = 'absolute';
            slotsText.style.top = '70px';
            slotsText.style.right = '20px';
            slotsText.style.background = '#e67e22';
            slotsText.style.color = 'white';
            slotsText.style.padding = '5px 15px';
            slotsText.style.borderRadius = '20px';
            slotsText.style.fontWeight = 'bold';
            slotsText.style.fontFamily = 'var(--font-heading)';
            slotsText.style.boxShadow = '0 4px 0 #d35400';
            document.body.appendChild(slotsText); // Append to body or stage
            // Ensure it's inside the game stage if possible, or body is fine (fixed pos)
            document.getElementById('stage-game').appendChild(slotsText);
        }
        slotsText.textContent = `🏆 ${slotsObj} TO QUALIFY`;

        gameActive = true;

        // Reset score for new round
        myScore = 0;
        console.log(`🎮 Starting game - Score reset to 0`);

        currentQuestionIndex = 0;
        this.updateProgress(0); // Reset dot

        // Re-enable all inputs (critical fix for multi-round)
        document.querySelectorAll('input, button').forEach(el => el.disabled = false);

        // Hide all modes & tracks first
        Object.values(modes).forEach(el => el.classList.add('hidden'));
        document.getElementById('track-container').style.display = 'none';

        // Dispatch based on Game Type
        switch (data.game_type) {
            case 'math_quiz':
                this.setupMathQuiz(data);
                break;
            case 'speed_typing':
                this.setupTyping(data);
                break;
            case 'tech_sprint':
                this.setupTechSprint(data);
                break;
            case 'true_false':
                this.setupTrueFalse(data);
                break;
            case 'fix_syntax':
                this.setupSyntax(data);
                break;
            default:
                console.error("Unknown game type:", data.game_type);
        }
    }

    // --- 1. MATH QUIZ ---
    static setupMathQuiz(data) {
        modes.math.classList.remove('hidden');
        questions = data.questions;

        const renderScaleQuestion = () => {
            if (!gameActive) return;
            // Loop questions if run out (for infinite feel in timed mode)
            const q = questions[currentQuestionIndex % questions.length];
            document.getElementById('math-problem').textContent = q.text;
            document.getElementById('math-input').value = '';
            document.getElementById('math-input').focus();
        };

        const submitMath = async () => {
            const val = document.getElementById('math-input').value;
            if (!val) return;

            // Optimistic scoring (Frontend guesses, Backend validates)
            const q = questions[currentQuestionIndex % questions.length];
            const isCorrect = parseInt(val) == q.answer;
            if (isCorrect) myScore++;
            else myScore = Math.max(0, myScore - 1);

            const input = document.getElementById('math-input');
            await this.showFeedback(input, isCorrect);

            socket.send('GAME_ACTION', {
                action: 'ANSWER',
                question_index: currentQuestionIndex % questions.length,
                answer: val
            });

            currentQuestionIndex++;
            renderScaleQuestion();
        };

        document.getElementById('math-submit').onclick = submitMath;
        document.getElementById('math-input').onkeydown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault(); // Prevent any form submission or page refresh
                submitMath();
            }
        };

        renderScaleQuestion();
    }

    // --- 2. SPEED TYPING ---
    static setupTyping(data) {
        modes.typing.classList.remove('hidden');
        const words = data.word_list;

        const renderWord = () => {
            if (!gameActive) return;
            // Infinite loop of words
            const target = words[currentQuestionIndex % words.length];

            const display = document.getElementById('typing-target');
            display.innerHTML = `<span style="font-size: 2em; color: white;">${target}</span>`;

            const input = document.getElementById('typing-input');
            input.value = '';
            input.placeholder = target;
            input.focus();
            input.disabled = false; // Re-enable for loop

            // Clear previous listener
            input.oninput = async () => {
                const val = input.value;
                if (val === target) {
                    input.disabled = true; // Prevent extra typing during flash
                    myScore++;
                    await this.showFeedback(input, true);

                    socket.send('GAME_ACTION', {
                        action: 'TYPE',
                        word_index: currentQuestionIndex % words.length,
                        word: val
                    });
                    currentQuestionIndex++;
                    renderWord();
                }
            };
        };

        renderWord();
    }

    // --- 3. TECH SPRINT ---
    static setupTechSprint(data) {
        modes.quiz.classList.remove('hidden');
        document.getElementById('track-container').style.display = 'flex'; // Show track
        questions = data.questions;

        this.renderQuizQuestion(data, async (isCorrect, btnElement) => {
            await this.showFeedback(btnElement, isCorrect);

            if (isCorrect) myScore++; // Move forward
            else myScore = Math.max(0, myScore - 1); // Move back

            this.updateProgress(myScore); // 0-10 Scale

            if (myScore >= 10) {
                this.finishGame(); // Win!
            }
        });
    }

    // --- 4. TRUE FALSE ---
    static setupTrueFalse(data) {
        modes.tf.classList.remove('hidden');
        questions = data.questions;

        const renderTF = () => {
            if (currentQuestionIndex >= questions.length) {
                // Loop if needed, or wait
                currentQuestionIndex = 0;
            }
            const q = questions[currentQuestionIndex];
            document.getElementById('tf-statement').textContent = q.text;
            document.getElementById('tf-score-goal').textContent = `${myScore}/10 Correct`;
        };

        const handleTF = async (choice, btnId) => {
            const q = questions[currentQuestionIndex];
            const isCorrect = (choice === q.answer);
            const btn = document.getElementById(btnId);

            await this.showFeedback(btn, isCorrect);

            if (isCorrect) myScore++;

            socket.send('GAME_ACTION', {
                action: 'ANSWER',
                question_index: currentQuestionIndex,
                answer: choice
            });

            currentQuestionIndex++;
            renderTF();

            if (myScore >= 10) this.finishGame(); // Win goal
        };

        document.getElementById('tf-true').onclick = () => handleTF('True', 'tf-true');
        document.getElementById('tf-false').onclick = () => handleTF('False', 'tf-false');

        renderTF();
    }

    // --- 5. FIX SYNTAX ---
    static setupSyntax(data) {
        modes.syntax.classList.remove('hidden');
        questions = data.questions;

        const renderSyntaxPuzzle = () => {
            if (!gameActive) return;
            const q = questions[currentQuestionIndex % questions.length];
            document.getElementById('syntax-code').textContent = q.code;
            const input = document.getElementById('syntax-input');
            input.value = '';
            input.focus();
        };

        const submitSyntax = async () => {
            const input = document.getElementById('syntax-input');
            const val = input.value.trim();
            if (!val) return;

            const q = questions[currentQuestionIndex % questions.length];
            const isCorrect = val == q.answer;

            await this.showFeedback(input, isCorrect);

            socket.send('GAME_ACTION', {
                action: 'ANSWER',
                question_index: currentQuestionIndex % questions.length,
                answer: val
            });

            // No immediate score feedback in UI for Syntax? Or maybe just flash?
            // Simple incremental:
            currentQuestionIndex++;
            renderSyntaxPuzzle();
        };

        document.getElementById('syntax-submit').onclick = submitSyntax;
        document.getElementById('syntax-input').onkeydown = (e) => {
            if (e.key === 'Enter') submitSyntax();
        };

        renderSyntaxPuzzle();
    }

    // --- HELPER: GENERIC QUIZ RENDERER ---
    static renderQuizQuestion(data, callback) {
        if (currentQuestionIndex >= questions.length) {
            currentQuestionIndex = 0; // Loop
        }

        const q = questions[currentQuestionIndex];
        document.getElementById('question-text').textContent = q.text;

        const grid = document.getElementById('answer-options');
        grid.innerHTML = '';

        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'answer-btn';
            btn.textContent = opt;
            btn.onclick = async () => {
                const isCorrect = (opt === q.answer);

                // Show feedback on THIS button
                await this.showFeedback(btn, isCorrect);

                callback(isCorrect, btn);

                socket.send('GAME_ACTION', {
                    action: 'ANSWER',
                    question_index: currentQuestionIndex,
                    answer: opt
                });

                currentQuestionIndex++;
                if (gameActive) this.renderQuizQuestion(data, callback);
            };
            grid.appendChild(btn);
        });
    }

    static updateProgress(score) {
        const pct = Math.min((score / 10) * 100, 100);
        document.getElementById('my-player-dot').style.left = `${pct}%`;
    }

    static finishGame() {
        if (!gameActive) return;
        console.trace('🏁 finishGame called from:');
        gameActive = false;
        console.log('🏁 Game Finished!');

        // Disable inputs
        document.querySelectorAll('input, button').forEach(el => el.disabled = true);

        // Notify Backend
        socket.send('ROUND_COMPLETE', { score: myScore });

        // Show "Qualified" Overlay (Wait Screen)
        const overlay = document.createElement('div');
        overlay.id = 'qualified-overlay'; // Add ID for cleanup
        overlay.style.position = 'absolute';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.background = 'rgba(46, 204, 113, 0.95)'; // Green tint
        overlay.style.display = 'flex';
        overlay.style.flexDirection = 'column';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '1000';
        overlay.style.animation = 'fadeIn 0.5s';

        overlay.innerHTML = `
            <div style="font-size: 5em;">✅</div>
            <h1 style="font-size: 3em; color: white; text-shadow: 2px 2px 0 rgba(0,0,0,0.2);">QUALIFIED!</h1>
            <p style="font-size: 1.5em; color: white;">Waiting for other players...</p>
            <div class="loading-spinner" style="margin-top: 20px;">
                <div class="spinner-ring" style="border-color: white; border-top-color: transparent;"></div>
            </div>
        `;

        document.getElementById('stage-game').appendChild(overlay);
    }

    static async runGameTimer(seconds) {
        const el = document.getElementById('game-timer');
        for (let i = seconds; i >= 0; i--) {
            if (!gameActive) break; // Stop if game finished early
            el.textContent = i;
            if (i <= 5) el.style.color = '#e74c3c'; // Red alert
            else el.style.color = '#f1c40f';
            await this.wait(1000);
        }
    }

    static showIntermission(data) {
        this.showStage('intermission');
        const intermissionStage = stages.intermission;
        intermissionStage.innerHTML = `
            <h1 style="font-size: 3em; margin: 0;">ROUND COMPLETE!</h1>
            <div style="font-size: 1.5em; margin: 20px 0; opacity: 0.8;">
                ${data.active_players} players remaining
            </div>
            ${data.next_round ? `<p>Next: Round ${data.next_round}</p>` : `<p>Final Round!</p>`}
        `;
    }

    static showGameEnd(data) {
        this.showStage('intermission');
        stages.intermission.innerHTML = `
            <div style="text-align: center;">
                <h1 style="font-size: 4em; color: var(--accent-yellow);">🏆 GAME OVER! 🏆</h1>
                <h2 style="font-size: 2.5em;">${data.winner ? data.winner.name + " WINS!" : "No Winner"}</h2>
                <button onclick="window.location.href='lobby.html'" style="margin-top:20px; padding:15px 30px; font-size:1.5em;" class="btn-academic">Back to Lobby</button>
            </div>
        `;
    }

    static wait(ms) { return new Promise(r => setTimeout(r, ms)); }

    static showFeedback(element, isCorrect) {
        return new Promise(resolve => {
            // 1. Text Overlay Feedback
            let overlay = document.getElementById('feedback-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'feedback-overlay';
                overlay.style.position = 'fixed';
                overlay.style.top = '50%';
                overlay.style.left = '50%';
                overlay.style.transform = 'translate(-50%, -50%)';
                overlay.style.fontSize = '4em';
                overlay.style.fontWeight = 'bold';
                overlay.style.textShadow = '2px 2px 4px rgba(0,0,0,0.5)';
                overlay.style.zIndex = '9999';
                overlay.style.pointerEvents = 'none';
                overlay.style.transition = 'opacity 0.2s, transform 0.2s';
                document.body.appendChild(overlay);
            }

            // Reset state
            overlay.style.opacity = '0';
            overlay.style.transform = 'translate(-50%, -50%) scale(0.5)';

            // Set Content
            if (isCorrect) {
                overlay.textContent = "✅ CORRECT!";
                overlay.style.color = '#2ecc71';
            } else {
                overlay.textContent = "❌ WRONG!";
                overlay.style.color = '#e74c3c';
            }

            // Animate In
            requestAnimationFrame(() => {
                overlay.style.opacity = '1';
                overlay.style.transform = 'translate(-50%, -50%) scale(1.2)';
            });

            // 2. Element Color Flash (Existing Logic)
            if (element) {
                const originalColor = element.style.backgroundColor;
                const originalBorder = element.style.borderColor;
                const originalTransition = element.style.transition;

                element.style.transition = 'background-color 0.2s, border-color 0.2s';

                if (isCorrect) {
                    element.style.backgroundColor = '#2ecc71'; // Green
                    element.style.borderColor = '#27ae60';
                } else {
                    element.style.backgroundColor = '#e74c3c'; // Red
                    element.style.borderColor = '#c0392b';
                }

                setTimeout(() => {
                    element.style.backgroundColor = originalColor || '';
                    element.style.borderColor = originalBorder || '';
                    element.style.transition = originalTransition || '';
                }, 500);
            }

            // Cleanup Overlay after 800ms
            setTimeout(() => {
                overlay.style.opacity = '0';
                overlay.style.transform = 'translate(-50%, -50%) scale(0.5)';
                resolve();
            }, 800);
        });
    }

    static showElimination() {
        this.showStage('intermission');
        stages.intermission.innerHTML = `
            <div style="text-align: center; animation: popIn 0.5s;">
                <h1 style="font-size: 5em; color: var(--accent-red); margin-bottom: 20px;">🚫 ELIMINATED 🚫</h1>
                <p style="font-size: 1.5em; margin-bottom: 30px;">Better luck next time!</p>
                <p>Returning to Lobby in 3s...</p>
                <div class="loading-spinner" style="width: 50px; height: 50px; margin: 0 auto; margin-top: 20px;">
                    <div class="spinner-ring" style="border-width: 4px;"></div>
                </div>
            </div>
        `;

        // Redirect back to the specific Waiting Room (Lobby)
        setTimeout(() => {
            window.location.href = `waiting_room.html?code=${sessionCode}`;
        }, 3000);
    }

    static runTimer(id, seconds) {
        return new Promise(resolve => {
            const el = document.getElementById(id);
            let t = seconds;
            el.textContent = t;
            const iv = setInterval(() => {
                t--;
                el.textContent = t;
                if (t <= 0) {
                    clearInterval(iv);
                    resolve();
                }
            }, 1000);
        });
    }
}

// --- SOCKET LISTENERS ---

let currentRoundNumber = 0;  // Track which round we're on
let pendingGameData = null;

socket.on('ROUND_START', (data) => {
    console.log('🎮 ROUND_START received for round:', data.round);

    // Only process if this is a NEW round
    if (data.round && data.round === currentRoundNumber) {
        console.log(`⚠️ Ignoring duplicate ROUND_START for round ${data.round}`);
        return;
    }

    // Update current round tracker
    currentRoundNumber = data.round;

    if (data.is_test_mode) {
        console.log('🧪 TEST MODE: Bypassing sync wait...');
        loadingManager.hide();
        GameFlow.startSequence(data);
        return;
    }

    pendingGameData = data;
    loadingManager.show('Waiting for all players to sync...');
    socket.send('PLAYER_READY_FOR_ROUND', { session_code: sessionCode, user_id: parseInt(userId) });
});

socket.on('ALL_PLAYERS_READY', () => {
    console.log('✅ All players ready!');
    loadingManager.hide();
    if (pendingGameData) {
        GameFlow.startSequence(pendingGameData);
        pendingGameData = null;
        // Don't reset currentRoundNumber here - it stays set for the entire round
    }
});

socket.connect(sessionCode, userId);

socket.onReady(() => {
    console.log('✓ WebSocket connected and ready!');
});

// Other listeners
socket.on('ROUND_RESULT', (data) => {
    console.log('📊 Received ROUND_RESULT:', data);

    // Check if this result is for current user
    if (data.user_id === parseInt(userId)) {
        console.log(`🎯 This is MY result! Status: ${data.status}, Rank: ${data.rank}`);

        // Remove the "waiting" overlay from finishGame
        const waitingOverlay = document.getElementById('qualified-overlay');
        if (waitingOverlay) waitingOverlay.remove();

        // Show QUALIFIED or ELIMINATED screen
        if (data.status === 'qualified') {
            // Show green QUALIFIED screen
            GameFlow.showStage('intermission');
            stages.intermission.style.background = 'linear-gradient(135deg, #2ecc71, #27ae60)';
            stages.intermission.innerHTML = `
                <div style="text-align: center; animation: popIn 0.5s;">
                    <h1 style="font-size: 5em; color: white; margin-bottom: 20px; text-shadow: 3px 3px 10px rgba(0,0,0,0.3);">✅ QUALIFIED! ✅</h1>
                    <h2 style="font-size: 3em; color: white; margin: 10px 0;">Rank #${data.rank} of ${data.total_players}</h2>
                    <p style="font-size: 2em; color: rgba(255,255,255,0.9); margin: 20px 0;">Score: ${data.score} points</p>
                    <p style="font-size: 1.5em; color: rgba(255,255,255,0.8);">Waiting for next round...</p>
                    <div class="loading-spinner" style="width: 50px; height: 50px; margin: 30px autoto; margin-top: 20px;">
                        <div class="spinner-ring" style="border-color: white; border-top-color: transparent; border-width: 4px;"></div>
                    </div>
                </div>
            `;
        } else {
            // Show red ELIMINATED screen
            GameFlow.showStage('intermission');
            stages.intermission.style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
            stages.intermission.innerHTML = `
                <div style="text-align: center; animation: popIn 0.5s;">
                    <h1 style="font-size: 5em; color: white; margin-bottom: 20px; text-shadow: 3px 3px 10px rgba(0,0,0,0.3);">❌ ELIMINATED ❌</h1>
                    <h2 style="font-size: 2.5em; color: white; margin: 10px 0;">Rank #${data.rank} of ${data.total_players}</h2>
                    <p style="font-size: 2em; color: rgba(255,255,255,0.9); margin: 20px 0;">Score: ${data.score} points</p>
                    <p style="font-size: 1.5em; color: rgba(255,255,255,0.8); margin-top: 30px;">Better luck next time!</p>
                    <p style="font-size: 1.2em; color: rgba(255,255,255,0.7);">Returning to waiting room...</p>
                    <div class="loading-spinner" style="width: 50px; height: 50px; margin: 0 auto; margin-top: 20px;">
                        <div class="spinner-ring" style="border-color: white; border-top-color: transparent; border-width: 4px;"></div>
                    </div>
                </div>
            `;

            // Redirect eliminated player to waiting room after 5 seconds
            setTimeout(() => {
                window.location.href = `waiting_room.html?code=${sessionCode}`;
            }, 5000);
        }
    }
});



socket.on('INTERMISSION', (data) => GameFlow.showIntermission(data));
socket.on('GAME_SESSION_END', (data) => GameFlow.showGameEnd(data));
socket.on('REDIRECT_TO_LOBBY', () => window.location.href = 'lobby.html');
