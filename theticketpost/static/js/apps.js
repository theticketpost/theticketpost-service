const { createApp } = Vue


const AppsApp = {
    data() {
        return {
            rawHtml: "",
            apps: [],
            config: {
                test: false
            }
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
            document.getElementById('app-configuration-title').innerHTML = componentId + " configuration";
            this.rawHtml = await response.text();
        },
        get_app_settings: async function(componentId) {
            console.log( componentId );
        },
        save_app_settings: async function() {
            //console.log( JSON.stringify(this.config) );
            const formData = new FormData(document.querySelector('form'))
            for (var pair of formData.entries()) {
              console.log(pair[0] + ': ' + pair[1]);
            }
            console.log("patata");
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
