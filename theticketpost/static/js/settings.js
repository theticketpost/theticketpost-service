const { createApp } = Vue

const SettingsApp = {
    data() {
        return {
            config: {
                webserver: {
                    port: 8080,
                },
                printer: {
                    device: null,
                    dpi: 200,
                    paper_width: 53,
                },
                schedule: {
                    monday: { active: false, time: "00:00" },
                    tuesday: { active: false, time: "00:00" },
                    wednesday: { active: false, time: "00:00" },
                    thursday: { active: false, time: "00:00" },
                    friday: { active: false, time: "00:00" },
                    saturday: { active: false, time: "00:00" },
                    sunday: { active: false, time: "00:00" },
                },
            },
            scan_disabled: false,
            devices: [],
        }
    },
    async created() {
        await this.get_settings();
    },
    delimiters: ['{', '}'],
    computed: {
        monday_active: function() {
            return !this.config.schedule.monday.active;
        },
        tuesday_active: function() {
            return !this.config.schedule.tuesday.active;
        },
        wednesday_active: function() {
            return !this.config.schedule.wednesday.active;
        },
        thursday_active: function() {
            return !this.config.schedule.thursday.active;
        },
        friday_active: function() {
            return !this.config.schedule.friday.active;
        },
        saturday_active: function() {
            return !this.config.schedule.saturday.active;
        },
        sunday_active: function() {
            return !this.config.schedule.sunday.active;
        }
    },
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
                body: JSON.stringify(this.config)
            });

        },
        get_settings: async function() {
            const response = await fetch('/api/settings/config', {
                method: 'GET'
            });

            response.json().then( json => {
                this.config = Object.assign( this.config, json);
                if (this.config.printer.device)
                    this.devices.push( this.config.printer.device );
            })
        }
    }
}

createApp(SettingsApp).mount('#settings-app');
