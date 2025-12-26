class GameSocket {
    constructor() {
        this.socket = null;
        this.listeners = {};
        this.onConnected = null;
        this.messageQueue = []; // Queue for offline messages
        this.isConnecting = false;
    }

    connect(sessionCode, userId) {
        if (this.isConnecting) return; // Prevent double connection attempts
        this.isConnecting = true;

        console.log(`Connecting with sessionCode: ${sessionCode}, userId: ${userId}`);

        if (!sessionCode || !userId) {
            console.error('❌ Cannot connect: missing sessionCode or userId!');
            this.isConnecting = false;
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/${sessionCode}/${userId}`;
        console.log(`WebSocket URL: ${url}`);
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            console.log('✓ WebSocket connected');
            this.isConnecting = false;

            // Send queued messages
            if (this.messageQueue.length > 0) {
                console.log(`📡 Sending ${this.messageQueue.length} queued messages...`);
                while (this.messageQueue.length > 0) {
                    const msg = this.messageQueue.shift();
                    this.send(msg.type, msg.payload);
                }
            }

            if (this.onConnected) {
                this.onConnected();
                // Don't clear onConnected if it's meant to be a permanent handler? 
                // Actually, existing logic clears it. Let's keep it that way for now.
                // But typically onReady might want to trigger every time?
                // The current implementation of onReady uses this for initial setup.
                this.onConnected = null;
            }
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('📩 RX:', data.type, data);
            this.trigger(data.type, data);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.isConnecting = false;
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket disconnected', event);
            this.isConnecting = false;

            // Try to reconnect if not clean close
            if (!event.wasClean) {
                console.log('🔄 Attempting to reconnect in 2s...');
                setTimeout(() => {
                    this.connect(sessionCode, userId);
                }, 2000);
            }
        };
    }

    onReady(callback) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            callback();
        } else {
            // Chain callbacks if multiple listeners attach? 
            // Current simplifiction: Overwrite. 
            // Better: Store in listeners? 
            // For now, let's just use the existing pattern but be mindful.
            const prev = this.onConnected;
            this.onConnected = () => {
                if (prev) prev();
                callback();
            };
        }
    }

    on(type, callback) {
        if (!this.listeners[type]) {
            this.listeners[type] = [];
        }
        this.listeners[type].push(callback);
    }

    trigger(type, data) {
        if (this.listeners[type]) {
            this.listeners[type].forEach(cb => cb(data));
        }
    }

    send(type, payload) {
        console.log(`📤 Attempting to send: ${type}`, payload);

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const message = JSON.stringify({ type, ...payload });
            console.log(`✅ Sending message raw:`, message);
            this.socket.send(message);
            console.log(`✓ Message sent to network`);
        } else {
            console.warn(`⚠️ WebSocket not ready (State: ${this.socket ? this.socket.readyState : 'NULL'}). Queueing message...`);
            this.messageQueue.push({ type, payload });
        }
    }
}

export const socket = new GameSocket();
