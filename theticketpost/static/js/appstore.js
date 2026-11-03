const { createApp } = Vue


const AppStoreApp = {
    data() {
        return {
            loaded: false,
            apps: [],
            filter: "all",
            installing: "",
            restart_required: false,
            restarting: false
        }
    },
    mounted() {
        this.get_appstore_apps();
    },
    delimiters: ['{', '}'],
    computed: {
        count_updates: function() {
            return this.apps.filter((app) => app.update).length;
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
