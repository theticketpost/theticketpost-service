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
            template: [],
            component_id: 0,
        }
    },
    mounted() {
        let element = document.getElementById('theModal');
        element.addEventListener('show.bs.modal', async (e) => {
            this.component_id = e.relatedTarget.getAttribute('data-component-id');
            this.get_component_inspector_form(this.component_id);
        });
        element.addEventListener('hidden.bs.modal', async (e) => {
            this.template = [];
            document.getElementById('component-configuration-form').reset();
        });

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
        get_component_inspector_form: async function( componentId ) {
            let jsonData = this.apps.at(componentId)["config"];
            this.template = jsonData;
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
        },
        preview_img: function(event) {
            preview_image = event.target.nextElementSibling;
            preview_image.src = URL.createObjectURL(event.target.files[0]);
            preview_image.onload = function() {
              URL.revokeObjectURL(preview_image.src) // free memory
            }
        },
        save_component_options: function() {
            let app = this.apps.at(this.component_id);

            // upload all files inside input file
            const input_files = document.getElementsByClassName("input-file");

            let all_done = new Promise( (resolve, reject) => {
        
                if ( input_files.length > 0 ) {
                    input_files.forEach( (input, key, array) => {
                        let file = input.files[0];
                        if ( file ) {
                            let formData = new FormData();
                            formData.append("file", file, file.name);
                            fetch('/api/apps/' + app.appname + '/upload', {method: "POST", body: formData}).then( (response)=> {
                                response.json().then( (json)=> {
                                    if ( json.code == 200 ) {
                                        let parameter = app["config"].find( element => element.name === input.id );
                                        if ( parameter ) {
                                            parameter["value"] = file.name;
                                            parameter["url"] = json.url;
                                        }
                                    }
                                    if ( key === array.length -1 ) resolve();
                                })
                            });
                        } else {
                            if ( key === array.length -1 ) resolve();
                        }
                    });
                } else {
                    resolve();
                }
            });

            all_done.then( () => {
                this.render_component(this.component_id, app.appname, app.config);
                document.getElementById('close-modal-button').click();
                this.$toast.open({
                    message: "Component updated",
                    type: "success",
                    duration: 5000,
                    position: "top-right",
                    dismissible: true
                })
            })
        }
    }
}

const app = createApp(NewspaperApp);
app.mount('#newspaper-app');
app.use(VueToast.ToastPlugin);
