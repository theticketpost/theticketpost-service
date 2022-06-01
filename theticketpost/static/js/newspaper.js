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
            print_disabled: false,
        }
    },
    async created() {
        await this.get_json()
        this.loaded = true;
    },
    delimiters: ['{', '}'],
    computed: {
        ticket_px_width: function() {
            if ( this.printer && this.printer.dpi && this.printer.paper_width ) {
                return Math.round( this.printer.dpi * this.printer.paper_width / 25.4 );
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
        add: function(title) {
            this.apps.push({ title: title, id: this.id++ });
            this.save_json();
        },
        del: function( index ) {
            this.apps.splice(index, 1);
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
            }

            this.print_disabled = false;

        }
    }
}

createApp(NewspaperApp).mount('#newspaper-app');
