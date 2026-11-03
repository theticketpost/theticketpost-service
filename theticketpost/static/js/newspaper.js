const { createApp } = Vue

// Used by the editor (home) and by the page the print pipeline screenshots (data-editable="false")
const root = document.getElementById('newspaper-app');

// what current() returns for a random section with no alternatives
const EMPTY_SECTION = Object.freeze({ appname: "", rawhtml: "", config: [] });

// a section's "days": the weekdays it prints on, 0 Monday to 6 Sunday (none: every day)
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_PLURALS = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"];

const NewspaperApp = {
    components: {
        vuedraggable,
    },
    data() {
        return {
            editable: root.dataset.editable === "true",
            loaded: false,
            config: {},
            apps: [],
            installed_apps: [],
            printing: false,
            selected: null,
            draft: [],
            applying: false,
            scale: 1,
            dragged: null,
            merge_target: null,
            // while dragging, tall sections shrink so they're easy to move around
            dragging: false,
            day_names: DAY_NAMES,
            // the same objects on every render (see ticket.html)
            ticket_group: { name: 'sections', pull: false },
            tiles_group: { name: 'sections', pull: 'clone', put: false },
        }
    },
    mounted() {
        // the ticket keeps its printed width: shrink the preview on narrow screens
        const fit = () => {
            const tray = this.$refs.tray;
            if (tray) this.scale = Math.min(1, (tray.clientWidth - 16) / (this.ticket_px_width + 48));  // 48: the paper's side margins
        };
        window.addEventListener('resize', fit);
        this.$watch('loaded', () => this.$nextTick(fit));
        this.$watch('ticket_px_width', fit);
    },
    async created() {
        await this.get_installed_apps();
        await this.get_json();

        // the printed page picks today's alternative of each random section
        if (!this.editable) {
            this.apps.forEach((element) => {
                if (this.is_group(element)) element.shown = this.pick(element);
            });
        }

        // refresh components if required (of a random section, the one shown)
        this.apps.forEach((element) => {
            const section = this.current(element);
            if (section.appname && (section.refresh_component || !section.rawhtml)) {
                this.render_component(section);
            }
        });

        this.loaded = true;
    },
    delimiters: ['{', '}'],
    computed: {
        device: function() {
            return !!(this.config.printer && this.config.printer.device);
        },
        ticket_px_width: function() {
            return this.device ? this.config.printer.device.dots_per_line : 384;
        },
        next_print: function() {
            return TTP.nextPrint(this.config.schedule);
        },
        weekday: function() {
            return (new Date().getDay() + 6) % 7;
        },
        today: function() {
            return new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
        },
        renderable_apps: function() {
            return this.installed_apps.filter((app) => app.render_component);
        },
        // why each top level section won't be printed today: "day" (not one of its
        // days), "empty" (its app has nothing to show), "linked" (it goes with a
        // neighbour that isn't printed) or null
        skip_reasons: function() {
            const reasons = new Array(this.apps.length).fill(undefined);
            const resolve = (index, visiting) => {
                if (reasons[index] !== undefined) return reasons[index];
                if (visiting.has(index)) return null;
                visiting.add(index);
                const element = this.apps[index];
                let reason = null;
                if (!this.prints_on(element, this.weekday)) {
                    reason = "day";
                } else if (this.is_empty(element)) {
                    reason = "empty";
                } else if (element.link === "next" || element.link === "prev") {
                    const neighbour = index + (element.link === "next" ? 1 : -1);
                    if (neighbour >= 0 && neighbour < this.apps.length && resolve(neighbour, visiting)) {
                        reason = "linked";
                    }
                }
                reasons[index] = reason;
                return reason;
            };
            this.apps.forEach((element, index) => resolve(index, new Set()));
            return reasons;
        },
        selected_element: function() {
            return this.selected === null ? null : (this.apps[this.selected] || null);
        },
        selected_group: function() {
            return this.is_group(this.selected_element) ? this.selected_element : null;
        },
        // the section the inspector edits: of a random section, the alternative shown
        selected_app: function() {
            return this.selected_element ? this.current(this.selected_element) : null;
        },
        selected_version: function() {
            if (!this.selected_app) return "";
            const app = this.installed_apps.find((app) => app.name === this.selected_app.appname);
            return app ? "v" + app.version : "not installed";
        }
    },
    watch: {
        selected_app: async function() {
            // edit a copy, applied with "Apply"
            const element = this.selected_app;
            this.draft = element ? JSON.parse(JSON.stringify(element.config || [])) : [];
            if (!element || !element.rawhtml) return;

            // sections saved before an app update miss its new options: add them
            // with their defaults, in the order of the app's current template
            try {
                const json = await TTP.getJSON('/api/apps/' + element.appname + '/inspector');
                if (this.selected_app !== element || !Array.isArray(json.config)) return;
                const saved = Object.fromEntries(this.draft.map((input) => [input.name, input]));
                this.draft = json.config.map((input) => saved[input.name]
                    ? { ...input, value: saved[input.name].value, url: saved[input.name].url ?? input.url }
                    : input);
            } catch (error) {}
        }
    },
    methods: {
        is_group: function(element) {
            return !!element && element.type === "group";
        },
        current: function(element) {
            if (!this.is_group(element)) return element;
            // never undefined: the ticket template reads .rawhtml of it
            return element.items[element.shown] || element.items[0] || EMPTY_SECTION;
        },
        pick: function(group) {
            const count = group.items.length;
            if (group.mode === "random") return Math.floor(Math.random() * count);
            // "daily": one after the other, a different one each day
            const now = new Date();
            const day = Math.floor((now.getTime() - now.getTimezoneOffset() * 60000) / 86400000);
            return day % count;
        },
        step: function(index, delta) {
            const group = this.apps[index];
            group.shown = (group.shown + delta + group.items.length) % group.items.length;
            this.selected = index;
            const section = this.current(group);
            if (!section.rawhtml) this.render_component(section);
            this.save_json();
        },
        make_group: function(index) {
            const section = this.apps[index];
            this.apps.splice(index, 1, { id: section.id, type: "group", mode: "daily", shown: 0, items: [section] });
            this.save_json();
            TTP.toast(this, "Now click an app in “Add a section” to add an alternative");
        },
        show_alternative: function(position) {
            this.selected_group.shown = position;
            const section = this.current(this.selected_group);
            if (!section.rawhtml) this.render_component(section);
            this.save_json();
        },
        remove_alternative: function(position) {
            const group = this.selected_group;
            group.items.splice(position, 1);
            if (group.items.length == 0) {
                // it was the only one: the whole section goes
                this.apps.splice(this.selected, 1);
                this.selected = null;
            } else if (group.items.length == 1) {
                // one alternative left: it's an ordinary section again
                this.apps.splice(this.selected, 1, group.items[0]);
            } else {
                group.shown = Math.min(group.shown, group.items.length - 1);
            }
            this.save_json();
        },
        ungroup: function() {
            // back to ordinary sections, one after another, where the group was
            const index = this.selected;
            const sections = this.selected_group.items;
            this.apps.splice(index, 1, ...sections);
            this.selected = null;
            this.save_json();
            sections.filter((section) => !section.rawhtml).forEach((section) => this.render_component(section));
            TTP.toast(this, "Split into " + sections.length + " sections");
        },
        take_out: function(position) {
            // that alternative becomes an ordinary section right after the group
            const index = this.selected;
            const group = this.selected_group;
            const [section] = group.items.splice(position, 1);
            this.apps.splice(index + 1, 0, section);
            if (!section.rawhtml) this.render_component(section);
            if (group.items.length == 1) {
                this.apps.splice(index, 1, group.items[0]);
            } else {
                group.shown = Math.min(group.shown, group.items.length - 1);
            }
            this.selected = null;
            this.save_json();
        },
        set_mode: function(mode) {
            this.selected_group.mode = mode;
            this.save_json();
        },
        is_empty: function(element) {
            // apps mark "nothing to show today" with a data-ttp-empty element
            const html = this.current(element).rawhtml || "";
            return html.includes("data-ttp-empty");
        },
        skip_reason: function(index) {
            return this.skip_reasons[index] || null;
        },
        has_days: function(element) {
            return Array.isArray(element.days) && element.days.length > 0 && element.days.length < 7;
        },
        prints_on: function(element, day) {
            return !this.has_days(element) || element.days.includes(day);
        },
        days_label: function(element) {
            const days = element.days;
            if (days.length == 1) return DAY_PLURALS[days[0]];
            if (days.join() == "0,1,2,3,4") return "weekdays";
            if (days.join() == "5,6") return "weekends";
            return days.map((day) => DAY_NAMES[day]).join(", ");
        },
        toggle_day: function(day) {
            const element = this.selected_element;
            const days = new Set(this.has_days(element) ? element.days : [0, 1, 2, 3, 4, 5, 6]);
            if (days.has(day)) days.delete(day);
            else days.add(day);
            // at least one day: a section that never prints is better removed
            if (days.size == 0) return;
            if (days.size == 7) delete element.days;
            else element.days = [...days].sort();
            this.save_json();
        },
        // the editor's line above a section: why it's left out today, or what it depends on
        print_note: function(index) {
            const element = this.apps[index];
            const neighbour = element.link === "next" ? "below" : "above";
            switch (this.skip_reason(index)) {
                case "day": return { icon: "#i-calendar", text: "Not printed today: only on " + this.days_label(element) };
                case "empty": return { icon: "#i-eye-off", text: "Not printed today: nothing to show" };
                case "linked": return { icon: "#i-link", text: "Not printed today: goes with the section " + neighbour };
            }
            const parts = [];
            if (this.has_days(element)) parts.push("only on " + this.days_label(element));
            if (element.link) parts.push("only with the section " + neighbour);
            if (!parts.length) return null;
            return { icon: this.has_days(element) ? "#i-calendar" : "#i-link", text: "Prints " + parts.join(", ") };
        },
        set_link: function(link) {
            if (link) this.selected_element.link = link;
            else delete this.selected_element.link;
            this.save_json();
        },
        clean: function(newspaper) {
            // random sections left without alternatives are dropped, and the one
            // shown is kept within range
            return newspaper.filter((element) => !this.is_group(element) || (Array.isArray(element.items) && element.items.length))
                .map((element) => {
                    if (this.is_group(element)) {
                        element.shown = Math.min(Math.max(Number(element.shown) || 0, 0), element.items.length - 1);
                    }
                    return element;
                });
        },
        select: function(index) {
            if (this.editable) this.selected = index;
        },
        new_section: function(app) {
            // placeholder until the app's inspector config arrives (see fill_section)
            return { id: 'new-' + Date.now(), appname: app.name, refresh_component: false, config: [], rawhtml: "" };
        },
        add: async function(appname) {
            const section = this.new_section({ name: appname });
            const group = this.selected_group;
            if (group) {
                // a random section is selected: the app becomes one more alternative
                group.items.push(section);
                group.shown = group.items.length - 1;
                await this.fill_section(this.selected);
                return;
            }
            // insert after the selected section, or at the end
            const index = this.selected === null ? this.apps.length : this.selected + 1;
            this.apps.splice(index, 0, section);
            await this.fill_section(index);
        },
        on_change: async function(event) {
            // a tile dropped from the "Add a section" panel
            if (!event.added) return;
            const index = event.added.newIndex;
            if (this.selected !== null && index <= this.selected) this.selected++;
            await this.fill_section(index);
        },
        fill_section: async function(index) {
            this.selected = index;
            const element = this.current(this.apps[index]);
            try {
                const json = await TTP.getJSON('/api/apps/' + element.appname + '/inspector');
                element.config = json.config;
                element.refresh_component = json.refresh_component;
                // the inspector opened before the options arrived: show them now
                if (this.selected_app === element) {
                    this.draft = JSON.parse(JSON.stringify(element.config || []));
                }
                await this.render_component(element);
            } catch (error) {
                TTP.toast(this, "Could not add " + element.appname + ": " + error.message, "error");
            }
        },
        del: function(index) {
            this.apps.splice(index, 1);
            this.selected = null;
            this.save_json();
        },
        refresh: function(element) {
            this.render_component(this.current(element));
        },
        drag_start: function(event) {
            // dropping a section on the middle of another one joins them in a
            // random section; near the edges it reorders as usual
            this.dragged = this.apps[event.oldIndex];
            this.merge_target = null;
            this.shrink(event.item);
            this._track = (e) => this.track_merge(e.touches ? e.touches[0] : e);
            document.addEventListener('pointermove', this._track);
            document.addEventListener('touchmove', this._track, { passive: true });
        },
        // tall sections shrink while dragging; the page scrolls so that the
        // section being dragged stays under the pointer
        shrink: function(item) {
            const before = item ? item.getBoundingClientRect().top : null;
            this.dragging = true;
            this.$nextTick(() => {
                if (item) window.scrollBy(0, item.getBoundingClientRect().top - before);
            });
        },
        // back to full size, keeping the section that was dropped where it was
        unshrink: function(item) {
            const before = item && item.isConnected ? item.getBoundingClientRect().top : null;
            this.dragging = false;
            // twice: a drop that joins a random section is applied on the next tick
            this.$nextTick(() => this.$nextTick(() => {
                const dropped = this.selected === null ? null : document.querySelectorAll('#newspaper .ticket-item')[this.selected];
                if (dropped && before !== null) window.scrollBy(0, dropped.getBoundingClientRect().top - before);
            }));
        },
        track_merge: function(point) {
            let target = null;
            for (const item of document.querySelectorAll('#newspaper .ticket-item')) {
                if (item.classList.contains('sortable-ghost') || item.classList.contains('sortable-chosen')) continue;
                const box = item.getBoundingClientRect();
                const band = box.height / 4;
                if (point.clientX >= box.left && point.clientX <= box.right &&
                    point.clientY >= box.top + band && point.clientY <= box.bottom - band) {
                    // by id: the list may have been reordered while dragging
                    target = this.apps.find((element) => String(element.id) === item.dataset.id) || null;
                    break;
                }
            }
            this.merge_target = target === this.dragged ? null : target;
        },
        allow_move: function(event, original) {
            // Sortable would swap as soon as the pointer touches the next
            // section, pushing it away before its middle (the merge zone) can be
            // reached. Swap only once the pointer is in the far quarter of the
            // section, the side it is moving towards.
            const point = original && (original.touches ? original.touches[0] : original);
            if (!point || point.clientY === undefined) return this.merge_target === null;
            this.track_merge(point);
            if (this.merge_target !== null) return false;
            const box = event.related.getBoundingClientRect();
            const quarter = box.height / 4;
            const moving_down = !!(event.dragged.compareDocumentPosition(event.related) & Node.DOCUMENT_POSITION_FOLLOWING);
            return moving_down ? point.clientY >= box.bottom - quarter : point.clientY <= box.top + quarter;
        },
        merge: function(dragged, target) {
            const incoming = this.is_group(dragged) ? dragged.items : [dragged];
            let group = target;
            if (this.is_group(target)) {
                target.items.push(...incoming);
            } else {
                group = { id: target.id, type: "group", mode: "daily", shown: 0, items: [target, ...incoming] };
                this.apps.splice(this.apps.indexOf(target), 1, group);
            }
            group.shown = group.items.length - incoming.length;
            this.apps.splice(this.apps.indexOf(dragged), 1);
            this.selected = this.apps.indexOf(group);
            const section = this.current(group);
            if (!section.rawhtml) this.render_component(section);
            this.save_json();
            TTP.toast(this, "Joined in a random section: a different one prints each day");
        },
        on_reorder: function(event) {
            document.removeEventListener('pointermove', this._track);
            document.removeEventListener('touchmove', this._track);
            this.unshrink(event.item);
            // where it was dropped counts too (a quick drag may not have moved over it)
            const drop = event.originalEvent;
            if (this.dragged && drop) {
                const point = drop.changedTouches ? drop.changedTouches[0] : drop;
                if (point && point.clientX !== undefined) this.track_merge(point);
            }
            const dragged = this.dragged, target = this.merge_target;
            this.dragged = this.merge_target = null;
            if (dragged && target && target !== dragged) {
                // wait for vuedraggable to apply any reorder made before reaching the target
                this.$nextTick(() => this.merge(dragged, target));
                return;
            }
            // keep the same section selected after the move
            const from = event.oldIndex, to = event.newIndex, sel = this.selected;
            if (sel === from) this.selected = to;
            else if (sel !== null && from < sel && to >= sel) this.selected = sel - 1;
            else if (sel !== null && from > sel && to <= sel) this.selected = sel + 1;
            this.save_json();
        },
        save_json: async function() {
            this.apps.forEach((element, index) => {
                element.id = index;
            });
            await TTP.postJSON('/api/settings/newspaper', this.apps);
        },
        get_json: async function() {
            this.config = await TTP.getJSON('/api/settings/config');

            const newspaper = await TTP.getJSON('/api/settings/newspaper');
            if (Array.isArray(newspaper)) {
                this.apps = this.clean(newspaper);
            }
        },
        print: async function() {
            this.printing = true;
            try {
                const response = await fetch('/api/printer/' + this.config.printer.device.address + '/print');
                TTP.toast(this, await response.text(), response.ok ? "success" : "error");
            } catch (error) {
                TTP.toast(this, "Could not reach the service", "error");
            }

            // the print renders the newspaper again: show what was printed
            await this.get_json();
            this.printing = false;
        },
        get_installed_apps: async function() {
            const json = await TTP.getJSON('/api/apps/installed');
            if (Array.isArray(json)) {
                this.installed_apps = json;
            }
        },
        render_component: async function(element) {
            const response = await TTP.postJSON('/api/apps/' + element.appname + '/component', element.config);
            element.rawhtml = await response.text();
            await this.save_json();
        },
        preview_img: function(event, input) {
            const file = event.target.files[0];
            input.preview = file ? URL.createObjectURL(file) : null;
        },
        upload_files: async function(appname) {
            // upload the images picked in the inspector
            for (const input of document.querySelectorAll(".input-file")) {
                const file = input.files[0];
                if (!file) continue;

                const formData = new FormData();
                formData.append("file", file, file.name);
                const response = await fetch('/api/apps/' + appname + '/upload', { method: "POST", body: formData });
                const json = await response.json();
                if (json.code != 200) {
                    throw new Error(json.msg);
                }

                const parameter = this.draft.find((element) => element.name === input.dataset.name);
                if (parameter) {
                    parameter.value = json.url.split('/').pop();
                    parameter.url = json.url;
                }
            }
        },
        apply: async function() {
            const element = this.selected_app;
            this.applying = true;
            try {
                await this.upload_files(element.appname);
                this.draft.forEach((input) => delete input.preview);
                element.config = JSON.parse(JSON.stringify(this.draft));
                await this.render_component(element);
                TTP.toast(this, "Section updated");
            } catch (error) {
                TTP.toast(this, "Could not update the section: " + error.message, "error");
            }
            this.applying = false;
        }
    }
}

const app = createApp(NewspaperApp);
app.use(VueToast.ToastPlugin);
app.mount('#newspaper-app');
