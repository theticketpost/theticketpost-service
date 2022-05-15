window.onload = function() {
const { createApp } = Vue

const NewspaperApp = {
    components: {
        vuedraggable,
    },
    data() {
        return {
            apps: []
        }
    },
    delimiters: ['{', '}'],
    methods: {
        add: function(title) {
            this.apps.push({ title: title });
        },
        del: function( ev ) {

        }
    }
}

createApp(NewspaperApp).mount('#newspaper-app');
}
