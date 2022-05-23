const { createApp } = Vue

const NewspaperApp = {
    components: {
        vuedraggable,
    },
    data() {
        return {
            id: 0,
            apps: []
        }
    },
    async created() {
        await this.get_json()
    },
    delimiters: ['{', '}'],
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
            const response = await fetch('/api/settings/newspaper', {
                method: 'GET'
            });
            const jsonData = await response.json();

            if (Array.isArray(jsonData)) {
                this.apps = jsonData;
                this.id = this.apps.length;
            }
        }
    }
}

createApp(NewspaperApp).mount('#newspaper-app');
