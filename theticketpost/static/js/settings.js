const { createApp } = Vue

const SettingsApp = {
    data() {
        return {
            config: {
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
                }
            },
            scan_disabled: false,
            devices: [],
            selected_device: null,
        }
    },
    async created() {
        await this.get_settings();
    },
    delimiters: ['{', '}'],
    computed: {
        monday_checked: function() {
            return !this.config.schedule.monday;
        },
        tuesday_checked: function() {
            return !this.config.schedule.tuesday;
        },
        wednesday_checked: function() {
            return !this.config.schedule.wednesday;
        },
        thursday_checked: function() {
            return !this.config.schedule.thursday;
        },
        friday_checked: function() {
            return !this.config.schedule.friday;
        },
        saturday_checked: function() {
            return !this.config.schedule.saturday;
        },
        sunday_checked: function() {
            return !this.config.schedule.sunday;
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
                //body: JSON.stringify(this)
            });
        },
        get_settings: async function() {
            const response = await fetch('/api/settings/config', {
                method: 'GET'
            });

            response.json().then( json => {
                this.printer_dpi = json.printer_dpi;
                this.printer_paper_width = json.printer_paper_width;
                this.schedule = json.schedule;
                this.selected_device = json.selected_device;
                console.log(json);
            })
        }
    }
}

createApp(SettingsApp).mount('#settings-app');
