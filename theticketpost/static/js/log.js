const { createApp } = Vue

const LogApp = {
    data() {
        return {
            log: ""
        }
    },
    async created() {
        await this.get_stream();
    },
    delimiters: ['{', '}'],
    methods: {
        get_stream: async function() {
            const response = await fetch('/api/log/stream', {
                method: 'GET'
            });
            const reader = response.body.getReader();

            while (true) {
              const { value, done } = await reader.read();
              if (done) break;

              let string = new TextDecoder().decode(value);
              document.getElementById("output").textContent += string;
            }

            console.log('Response fully received');
        }
    }

}

createApp(LogApp).mount('#log-app');
