const { createApp } = Vue


const AppsApp = {
    data() {
        return {
            loaded: false,
            apps: [],
            updates: {},
            template: [],
            componentId: "",
            confirming: null,
            removing: false,
            providers: []
        }
    },
    mounted() {
        this.get_installed_apps();
        this.get_updates();
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.componentId) this.close_settings();
        });
    },
    delimiters: ['{', '}'],
    computed: {
        needing_setup: function() {
            return this.apps.filter((app) => app.needs_setup);
        }
    },
    methods: {
        open_settings: async function(componentId) {
            this.template = await TTP.getJSON('/api/apps/' + componentId + '/configuration');
            this.template.forEach((input) => {
                if (input.type === 'url-list' && !Array.isArray(input.value)) input.value = [];
            });
            if (this.template.some((input) => input.type === 'llm-provider')) {
                try { this.providers = await TTP.getJSON('/api/llm/providers'); } catch (error) {}
            }
            this.componentId = componentId;
        },
        usable_providers: function(input) {
            // the ones with a key, plus the one the app has now so the select shows it
            return this.providers.filter((provider) => provider.configured || provider.id === input.value);
        },
        default_model: function() {
            const input = this.template.find((input) => input.type === 'llm-provider');
            const provider = input && this.providers.find((provider) => provider.id === input.value);
            return provider ? provider.default_model : '';
        },
        provider_changed: function() {
            // a model name only makes sense for its provider
            const model = this.template.find((input) => input.name === 'model');
            if (model) model.value = '';
        },
        close_settings: function() {
            this.componentId = "";
            this.template = [];
        },
        save_app_settings: async function() {
            const response = await TTP.postJSON('/api/settings/config?app=' + this.componentId, this.template);
            TTP.toast(this, response.ok ? "Settings for " + this.componentId + " saved" : "Could not save the settings", response.ok ? "success" : "error");
            this.close_settings();
            this.get_installed_apps();
        },
        uninstall: async function(app_name) {
            this.removing = true;
            const response = await fetch('/api/apps/uninstall/' + app_name);
            TTP.toast(this, await response.text(), response.ok ? "success" : "error");
            this.removing = false;
            this.confirming = null;
            this.get_installed_apps();
        },
        deleteCredential(credentials, index) {
            credentials.splice(index, 1);
        },
        handleCredentialUpload: function(event, index) {
            const file = event.target.files[0];
            const reader = new FileReader();
            reader.onload = async () => {
                const obj = {
                    name: '',
                    credential: JSON.parse(reader.result),
                    token: ''
                };
                try {
                    const response = await TTP.postJSON("/api/google-auth/get-token", { credential: obj.credential, scopes: this.template[index].scopes });
                    const data = await response.json();
                    obj.token = data.access_token;
                    this.template[index].value.push(obj);
                } catch (error) {
                    TTP.toast(this, "Could not get a Google token", "error");
                }
            };
            reader.readAsText(file);
        },
        get_installed_apps: async function() {
            const json = await TTP.getJSON('/api/apps/installed');
            if (Array.isArray(json)) {
                this.apps = json;
            }
            this.loaded = true;
        },
        get_updates: async function() {
            try {
                const store = await TTP.getJSON('/api/appstore/apps');
                const updates = {};
                store.filter((app) => app.update).forEach((app) => { updates[app.desc.name] = app.desc.version; });
                this.updates = updates;
            } catch (error) {}
        }
    }
}

const app = createApp(AppsApp);
app.use(VueToast.ToastPlugin);
app.mount('#apps-app');
