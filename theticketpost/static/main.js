
const { createApp } = Vue

const NewspaperApp = {
    data() {
        return {
            apps: []
        }
    },
    delimiters: ['{', '}'],
    methods: {
        add: function() {
            this.apps.push({ title: "test" });
        }
    }
}

createApp(NewspaperApp).mount('#newspaper-app');
