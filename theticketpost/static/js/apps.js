const { createApp } = Vue

const AppsApp = {
    data() {
        return {
            apps: [],
        }
    },
    async created() {
        await this.get_installed_apps()
    },
    delimiters: ['{', '}'],
    methods: {
        get_installed_apps: async function() {
            let response = await fetch('/api/apps/installed', {
                method: 'GET'
            });
            let jsonData = await response.json();

            if (Array.isArray(jsonData)) {
                this.apps = jsonData;
            }
        }
    }
}

const app = createApp(AppsApp);
app.mount('#apps-app');
app.use(VueToast.ToastPlugin);
