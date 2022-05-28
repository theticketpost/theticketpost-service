const { createApp } = Vue

const LogApp = {
    async created() {
        await this.get_log_stream();
    },
    delimiters: ['{', '}'],
    methods: {
        get_log_stream: async function() {
            const response = await fetch('/api/log/stream', {
                method: 'GET'
            });
            const reader = response.body.getReader();

            while (true) {
              const { value, done } = await reader.read();
              if (done) break;

              let string = new TextDecoder().decode(value);
              var element = document.getElementById("output");
              element.textContent += string;
              element.scrollTop = element.scrollHeight;
            }

            console.log('Response fully received');
        },
        reset_log: async function()  {
            const response = await fetch('/api/log/reset', {
                method: 'GET'
            });
        }
    }

}

createApp(LogApp).mount('#log-app');
