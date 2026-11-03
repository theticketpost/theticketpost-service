const { createApp } = Vue


const AppStoreApp = {
    data() {
        return {
            loaded: false,
            apps: [],
            filter: "all",
            installing: "",
            restart_required: false,
            restarting: false,
            checking: false,
            checked_at: null
        }
    },
    mounted() {
        this.get_appstore_apps();
        // read the catalog again when it's more than 10 minutes old
        this.check_for_updates(600, true);
    },
    delimiters: ['{', '}'],
    computed: {
        count_updates: function() {
            return this.apps.filter((app) => app.update).length;
        },
        checked_label: function() {
            if (!this.checked_at) return "";
            const date = new Date(this.checked_at * 1000);
            const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            return date.toDateString() == new Date().toDateString() ? "Checked at " + time : "Checked " + date.toLocaleDateString() + " " + time;
        },
        visible: function() {
            if (this.filter == "updates") return this.apps.filter((app) => app.update);
            if (this.filter == "new") return this.apps.filter((app) => !app.update);
            return this.apps;
        }
    },
    methods: {
        get_appstore_apps: async function() {
            try {
                const [store, installed] = await Promise.all([TTP.getJSON('/api/appstore/apps'), TTP.getJSON('/api/apps/installed')]);
                const versions = {};
                installed.forEach((app) => { versions[app.name] = app.version; });
                store.forEach((app) => { app.installed_version = versions[app.desc.name]; });
                // updates first
                this.apps = store.sort((a, b) => (b.update - a.update) || a.desc.name.localeCompare(b.desc.name));
            } catch (error) {
                this.apps = [];
            }
            this.loaded = true;
        },
        // quiet: when the page asks on its own, the list just updates
        check_for_updates: async function(max_age = 0, quiet = false) {
            if (this.checking) return;
            this.checking = true;
            const before = new Set(this.apps.map((app) => app.desc.name + "@" + app.desc.version));
            try {
                const response = await fetch('/api/appstore/refresh?max_age=' + max_age, { method: 'POST' });
                let status = await response.json();
                while (status.loading) {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    status = await TTP.getJSON('/api/appstore/status');
                }
                this.checked_at = status.checked_at;
                await this.get_appstore_apps();
                TTP.showUpdateCount();
                if (quiet) return;
                const found = this.apps.filter((app) => !before.has(app.desc.name + "@" + app.desc.version)).length;
                if (status.error) {
                    TTP.toast(this, "Could not check the store: " + status.error, "error");
                } else if (found) {
                    TTP.toast(this, found == 1 ? "1 new app or update" : found + " new apps or updates", "info");
                } else {
                    TTP.toast(this, "The store is up to date", "success");
                }
            } catch (error) {
                if (!quiet) TTP.toast(this, "Could not check the store", "error");
            } finally {
                this.checking = false;
            }
        },
        install: async function(app_name) {
            this.installing = app_name;
            try {
                const response = await fetch('/api/appstore/install/' + app_name);
                const result = await response.json();
                if (result.restart_required) {
                    this.restart_required = true;
                }
                TTP.toast(this, result.message, response.ok ? "success" : "error");
            } catch (error) {
                TTP.toast(this, "Error installing " + app_name, "error");
            } finally {
                this.installing = "";
                this.get_appstore_apps();
            }
        },
        restart: async function() {
            this.restarting = true;
            await fetch('/api/restart', { method: 'POST' });

            // Wait until the service answers again
            const wait = async () => {
                try {
                    const response = await fetch('/api/apps/installed');
                    if (response.ok) {
                        window.location.reload();
                        return;
                    }
                } catch (error) {}
                setTimeout(wait, 2000);
            };
            setTimeout(wait, 3000);
        }
    }
}

const app = createApp(AppStoreApp);
app.use(VueToast.ToastPlugin);
app.mount('#appstore-app');
