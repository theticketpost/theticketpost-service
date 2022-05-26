const { createApp } = Vue

const SettingsApp = {
    data() {
        return {
            config: {
                printer: {
                    device: null,
                    dpi: 200,
                    paper_width: 53,
                },
                schedule: {
                    monday: { checked: false, time: "00:00" },
                    tuesday: { checked: false, time: "00:00" },
                    wednesday: { checked: false, time: "00:00" },
                    thursday: { checked: false, time: "00:00" },
                    friday: { checked: false, time: "00:00" },
                    saturday: { checked: false, time: "00:00" },
                    sunday: { checked: false, time: "00:00" },
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
        monday_checked: function() {
            return !this.config.schedule.monday.checked;
        },
        tuesday_checked: function() {
            return !this.config.schedule.tuesday.checked;
        },
        wednesday_checked: function() {
            return !this.config.schedule.wednesday.checked;
        },
        thursday_checked: function() {
            return !this.config.schedule.thursday.checked;
        },
        friday_checked: function() {
            return !this.config.schedule.friday.checked;
        },
        saturday_checked: function() {
            return !this.config.schedule.saturday.checked;
        },
        sunday_checked: function() {
            return !this.config.schedule.sunday.checked;
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
            })
        }
    }
}

createApp(SettingsApp).mount('#settings-app');
