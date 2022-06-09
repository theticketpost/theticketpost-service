const { createApp } = Vue

const AppsApp = {
    data() {
        return {
            apps: [],
        }
    },
    async created() {
        this.get_installed_apps();

        let element = document.getElementById('theModal');
        element.addEventListener('show.bs.modal', async (e) => {
            let componentId = e.relatedTarget.getAttribute('data-component-id');
            let response = await fetch('/api/apps/' + componentId + '/configuration')
            document.getElementById('app-configuration-title').innerHTML = componentId + " configuration";
            document.getElementById('app-configuration-form').innerHTML = await response.text();
        });
    },
    delimiters: ['{', '}'],
    methods: {
        get_app_settings: async function(componentId) {
        },
        get_installed_apps: async function() {
            let response = await fetch('/api/apps/installed', {
                method: 'GET'
            });
            let jsonData = await response.json();

            if (Array.isArray(jsonData)) {
                this.apps = jsonData;
            }
        },
        open_modal: async function() {
            let modal = document.getElementById('theModal');

        }
    }
}

const app = createApp(AppsApp);
app.mount('#apps-app');
app.use(VueToast.ToastPlugin);
