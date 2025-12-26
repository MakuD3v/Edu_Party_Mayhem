export class UI {
    static show(elementId) {
        document.getElementById(elementId).classList.remove('hidden');
    }

    static hide(elementId) {
        document.getElementById(elementId).classList.add('hidden');
    }

    static setVal(elementId, value) {
        document.getElementById(elementId).value = value;
    }

    static getVal(elementId) {
        return document.getElementById(elementId).value;
    }
}
