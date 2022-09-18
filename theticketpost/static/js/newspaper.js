const { createApp } = Vue

const NewspaperApp = {
    components: {
        vuedraggable,
    },
    data() {
        return {
            loaded: false,
            printer: null,
            id: 0,
            apps: [],
            installed_apps: [],
            print_disabled: false,
        }
    },
    async created() {
        await this.get_installed_apps();
        await this.get_json()
        this.loaded = true;
    },
    delimiters: ['{', '}'],
    computed: {
        ticket_px_width: function() {
            if ( this.printer && this.printer.device ) {
                return this.printer.device.dots_per_line
            } else {
                return 0;
            }
        },
        device: function() {
            if ( this.printer )
                return this.printer.device != null;
            else
                return false;
        }
    },
    methods: {
        add: function(appname) {
            fetch('/api/apps/' + appname + '/inspector').then( (response) => {
                response.json().then( (json) => {
                    this.apps.push({ id: this.id++, appname: appname, config: json, rawhtml: "" });
                    this.id = this.apps.length;
                    this.render_component(this.id-1, appname, json);
                    this.save_json();
                })
            })
        },
        del: function( index ) {
            this.apps.splice(index, 1);
            this.id = this.apps.length;
            this.save_json();
        },
        save_json: async function() {
            this.apps.forEach( (element, index) => {
                element.id = index;
            });
            const response = await fetch('/api/settings/newspaper', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.apps)
            });
        },
        get_json: async function() {
            let response = await fetch('/api/settings/config', {
                method: 'GET'
            });
            let jsonData = await response.json();

            this.printer = jsonData.printer;

            response = await fetch('/api/settings/newspaper', {
                method: 'GET'
            });
            jsonData = await response.json();

            if (Array.isArray(jsonData)) {
                this.apps = jsonData;
                this.id = this.apps.length;
            }
        },
        print: async function() {
            this.print_disabled = true;

            let response = await fetch('/api/settings/config', {
                method: 'GET'
            });

            const jsonData = await response.json();

            if (jsonData.printer.device) {
                const printer_address = jsonData.printer.device.address;

                response = await fetch('/api/printer/' + printer_address + '/print', {
                    method: 'GET'
                });

                type = response.status == 200 ? "success" : "error";

                const text = await response.text();

                this.$toast.open({
                    message: text,
                    type: type,
                    duration: 5000,
                    position: "top-right",
                    dismissible: true
                })
            }

            this.print_disabled = false;

        },
        get_installed_apps: async function() {
            let response = await fetch('/api/apps/installed', {
                method: 'GET'
            });
            let jsonData = await response.json();

            if (Array.isArray(jsonData)) {
                this.installed_apps = jsonData;
            }
        },
        render_component: function(id, appname, config) {
            fetch('/api/apps/' + appname + '/component', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify( config ) } ).then( (response) => {
                response.text().then( (rawhtml) => {
                    this.apps.at(id)["rawhtml"] = rawhtml;
                    this.save_json();
                });
            })
        }
    }
}

const app = createApp(NewspaperApp);
app.mount('#newspaper-app');
app.use(VueToast.ToastPlugin);
