// Shared by every page: sidebar status and small helpers.

const TTP = {
    DAYS: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],

    toast(vm, message, type = "success") {
        vm.$toast.open({ message: message, type: type, duration: 5000, position: "top-right", dismissible: true });
    },

    async getJSON(url) {
        const response = await fetch(url);
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    async postJSON(url, data) {
        return fetch(url, {
            method: "POST",
            headers: { "Accept": "application/json", "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    // Number of store updates on the sidebar badge
    async showUpdateCount() {
        try {
            const apps = await TTP.getJSON("/api/appstore/apps");
            const updates = apps.filter((app) => app.update).length;
            document.querySelectorAll("[data-update-count]").forEach((element) => {
                element.textContent = updates;
                element.hidden = updates === 0;
            });
        } catch (error) {}
    },

    // Next scheduled print as "Tue 08:00", or null
    nextPrint(schedule, now = new Date()) {
        if (!schedule) return null;
        for (let offset = 0; offset < 8; offset++) {
            const date = new Date(now);
            date.setDate(now.getDate() + offset);
            const day = TTP.DAYS[(date.getDay() + 6) % 7];
            const entry = schedule[day];
            if (!entry || !entry.active || !entry.time) continue;
            const [hours, minutes] = entry.time.split(":").map(Number);
            date.setHours(hours, minutes, 0, 0);
            if (date <= now) continue;
            const label = offset === 0 ? "Today" : offset === 1 ? "Tomorrow" : date.toLocaleDateString("en-GB", { weekday: "short" });
            return label + " " + entry.time;
        }
        return null;
    }
};

document.addEventListener("DOMContentLoaded", async () => {
    try {
        const config = await TTP.getJSON("/api/settings/config");
        const device = config.printer && config.printer.device;
        document.querySelectorAll("[data-printer-status]").forEach((element) => {
            element.querySelector(".dot").classList.toggle("off", !device);
            element.querySelector("span:last-child").textContent = device ? device.name : "No printer";
        });
    } catch (error) {}

    TTP.showUpdateCount();
});
