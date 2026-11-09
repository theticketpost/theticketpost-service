const { createApp } = Vue

function default_config() {
    const schedule = {};
    TTP.DAYS.forEach((day) => { schedule[day] = { active: false, time: "08:00" }; });
    return {
        repository: { name: 'theticketpost/theticketpost-apps' },
        webserver: { port: 8080 },
        printer: { device: null, density: 3, pace: true },
        renderer: { chromium_path: "" },
        schedule: schedule,
        llm: {},
    };
}

const SettingsApp = {
    data() {
        return {
            config: default_config(),
            saved: "",
            config_warning: false,
            scanning: false,
            saving: false,
            restarting: false,
            devices: [],
            providers: [],
            backup_parts: { settings: true, newspaper: true },
            importing: false,
            days: TTP.DAYS.map((day) => ({ key: day, name: day.charAt(0).toUpperCase() + day.slice(1), short: day.charAt(0).toUpperCase() + day.slice(1, 3) })),
        }
    },
    async created() {
        try {
            this.providers = await TTP.getJSON('/api/llm/providers');
        } catch (error) {}
        await this.get_settings();
    },
    delimiters: ['{', '}'],
    computed: {
        next_print: function() {
            return TTP.nextPrint(this.config.schedule);
        },
        export_url: function() {
            const parts = Object.keys(this.backup_parts).filter((part) => this.backup_parts[part]);
            return parts.length ? '/api/backup/export?parts=' + parts.join(',') : '';
        },
        dirty: function() {
            return this.saved !== "" && JSON.stringify(this.config) !== this.saved;
        }
    },
    methods: {
        provider_ready: function(provider) {
            const settings = this.config.llm[provider.id] || {};
            return provider.needs_key ? !!settings.api_key : !!settings.enabled;
        },
        is_selected: function(device) {
            return !!this.config.printer.device && this.config.printer.device.address === device.address;
        },
        is_saved: function(device) {
            const saved = this.saved ? JSON.parse(this.saved).printer.device : null;
            return !!saved && saved.address === device.address;
        },
        scan_for_devices: async function() {
            this.scanning = true;
            const response = await fetch('/api/printer/scan');
            this.scanning = false;

            if (response.ok) {
                const found = await response.json();
                // keep the selected printer in the list even when it isn't found
                const selected = this.config.printer.device;
                if (selected && !found.some((device) => device.address === selected.address)) {
                    found.unshift(selected);
                }
                this.devices = found;
                if (found.length == 0) TTP.toast(this, "No printers found", "info");
            } else {
                TTP.toast(this, await response.text(), "error");
            }
        },
        save_settings: async function() {
            this.saving = true;
            const response = await TTP.postJSON('/api/settings/config', this.config);
            this.saving = false;
            if (response.ok) {
                this.saved = JSON.stringify(this.config);
                this.config_warning = false;
                TTP.toast(this, "Settings saved");
            } else {
                TTP.toast(this, "Could not save the settings", "error");
            }
        },
        import_backup: async function(event) {
            const file = event.target.files[0];
            event.target.value = "";
            if (!file) return;
            this.importing = true;
            try {
                const form = new FormData();
                form.append("file", file, file.name);
                const response = await fetch('/api/backup/import', { method: 'POST', body: form });
                if (!response.ok) {
                    TTP.toast(this, await response.text(), "error");
                    return;
                }
                const report = await response.json();
                let message = "Imported: " + report.parts.join(" and ");
                if (report.installed.length) message += ". Installed " + report.installed.join(", ");
                TTP.toast(this, message);
                if (report.missing.length) {
                    TTP.toast(this, "Not in the app store, sections that use them won't print: " + report.missing.join(", "), "error");
                }
                if (report.restart) {
                    TTP.toast(this, "Restart the service to use the updated libraries", "info");
                }
                if (report.parts.includes("settings")) {
                    await this.get_settings();
                }
            } catch (error) {
                TTP.toast(this, "Could not import the backup", "error");
            } finally {
                this.importing = false;
            }
        },
        restart: async function() {
            this.restarting = true;
            await fetch('/api/restart', { method: 'POST' });
            const wait = async () => {
                try {
                    const response = await fetch('/api/apps/installed');
                    if (response.ok) {
                        this.restarting = false;
                        TTP.toast(this, "Service restarted");
                        return;
                    }
                } catch (error) {}
                setTimeout(wait, 2000);
            };
            setTimeout(wait, 3000);
        },
        get_settings: async function() {
            const json = await TTP.getJSON('/api/settings/config');
            if (Object.keys(json).length > 0) {
                const config = default_config();
                // merge section by section, so settings saved by older versions get the new keys
                Object.keys(json).forEach((key) => {
                    config[key] = (config[key] && typeof config[key] === "object" && json[key] && typeof json[key] === "object")
                        ? Object.assign(config[key], json[key])
                        : json[key];
                });
                TTP.DAYS.forEach((day) => {
                    config.schedule[day] = Object.assign({ active: false, time: "08:00" }, config.schedule[day] || {});
                });
                this.config = config;
                if (config.printer.device) {
                    this.devices = [config.printer.device];
                }
            } else {
                this.config_warning = true;
            }
            this.providers.forEach((provider) => {
                this.config.llm[provider.id] = Object.assign({ api_key: "", base_url: "", enabled: false }, this.config.llm[provider.id] || {});
            });
            this.saved = JSON.stringify(this.config);
        }
    }
}

const app = createApp(SettingsApp);
app.use(VueToast.ToastPlugin);
app.mount('#settings-app');
