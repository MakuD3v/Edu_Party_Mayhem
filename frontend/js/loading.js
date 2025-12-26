/**
 * Loading Screen Manager
 * Provides a reusable loading overlay for async operations
 */

class LoadingManager {
    constructor() {
        this.overlay = null;
        this.messageElement = null;
        this.init();
    }

    init() {
        // Create loading overlay element
        this.overlay = document.createElement('div');
        this.overlay.id = 'loading-overlay';
        this.overlay.className = 'loading-overlay hidden';

        this.overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner">
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                    <div class="spinner-icon">📚</div>
                </div>
                <div class="loading-message">Loading...</div>
            </div>
        `;

        document.body.appendChild(this.overlay);
        this.messageElement = this.overlay.querySelector('.loading-message');
    }

    show(message = 'Loading...') {
        if (this.overlay) {
            this.messageElement.textContent = message;
            this.overlay.classList.remove('hidden');
            // Prevent body scroll when loading
            document.body.style.overflow = 'hidden';
        }
    }

    hide() {
        if (this.overlay) {
            this.overlay.classList.add('hidden');
            // Restore body scroll
            document.body.style.overflow = '';
        }
    }

    updateMessage(message) {
        if (this.messageElement) {
            this.messageElement.textContent = message;
        }
    }

    // Show loading for a minimum duration (prevents flash for fast operations)
    async showMinimum(message = 'Loading...', minDuration = 500) {
        const startTime = Date.now();
        this.show(message);

        return {
            hide: async () => {
                const elapsed = Date.now() - startTime;
                const remaining = minDuration - elapsed;

                if (remaining > 0) {
                    await new Promise(resolve => setTimeout(resolve, remaining));
                }

                this.hide();
            }
        };
    }
}

// Create global instance
const loadingManager = new LoadingManager();

// Export for use in other modules
export default loadingManager;
