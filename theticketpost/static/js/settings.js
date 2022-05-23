const { createApp } = Vue

const SettingsApp = {
    data() {
        return {
            printer_dpi: 200,
            printer_paper_width: 53,
            schedule: {
                monday: false,
                tuesday: false,
                wednesday: false,
                thursday: false,
                friday: false,
                saturday: false,
                sunday: false,
            },
            scan_disabled: false,
            devices: [],
        }
    },
    async created() {
        await this.get_settings();
    },
    delimiters: ['{', '}'],
    methods: {
        scan_for_devices: async function() {
            this.scan_disabled = true;

            const response = await fetch('/api/printer/scan', {
                method: 'GET'
            });

            response.json().then( json => {
                this.devices = json;
                this.scan_disabled = false;
            })
        },
        save_settings: async function() {

            const response = await fetch('/api/settings/config', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                //body: JSON.stringify(this)
            });
        },
        get_settings: async function() {
            const response = await fetch('/api/settings/config', {
                method: 'GET'
            });

            response.json().then( json => {
                console.log(json);
            })
        }
    }
}

createApp(SettingsApp).mount('#settings-app');
