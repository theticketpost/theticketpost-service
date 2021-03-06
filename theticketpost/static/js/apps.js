const { createApp } = Vue


const AppsApp = {
    data() {
        return {
            apps: [],
            template: [],
            componentId: ""
        }
    },
    mounted() {
        this.get_installed_apps();

        let element = document.getElementById('theModal');
        element.addEventListener('show.bs.modal', async (e) => {
            let componentId = e.relatedTarget.getAttribute('data-component-id');
            this.get_app_form(componentId);
        });
    },
    delimiters: ['{', '}'],
    methods: {
        get_app_form: async function( componentId ) {
            let response = await fetch('/api/apps/' + componentId + '/configuration')
            let jsonData = await response.json();
            this.template = jsonData;
            this.componentId = componentId;
        },
        get_app_settings: async function(componentId) {
            console.log( componentId );
        },
        save_app_settings: async function() {
            const response = await fetch('/api/settings/config?app=' + this.componentId, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.template)
            });

            this.$toast.open({
                message: "Settings for " + this.componentId + " updated",
                type: "success",
                duration: 5000,
                position: "top-right",
                dismissible: true
            })

        },
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
