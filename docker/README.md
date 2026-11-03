# Docker

Commands are run from the repository root.

## Build and run

```bash
docker build -f docker/Dockerfile -t theticketpost-service .
docker run -d --name theticketpost -p 8080:8080 -e TZ=Europe/Madrid \
    -v theticketpost-data:/data theticketpost-service
```

Or with compose:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Open `http://localhost:8080`.

- `/data` is the service's `~/.theticketpost`: settings, installed apps, logs and the last printed ticket. It survives image rebuilds.
- Set `TZ`: the scheduler prints at the container's local time.
- The service listens on the port in the settings (8080 by default). If you change it, change the port mapping too.
- Libraries that apps need are pip-installed when the container starts, so the first start after recreating the container takes longer.
- If you bind-mount a host folder on `/data` instead of a named volume, it must be writable by uid 1000.

## Bluetooth printing

The container uses the host's Bluetooth stack (BlueZ) through D-Bus, so the host needs `bluetooth` running. Two things are needed:

1. Mount the D-Bus socket: `-v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket`.
2. On hosts with AppArmor (Ubuntu, Debian, Raspberry Pi OS...), Docker's default profile blocks D-Bus. Without changes the printer scan fails with `org.freedesktop.DBus.Error.AccessDenied: An AppArmor policy prevents this sender...`. Run the container with `--security-opt apparmor=unconfined`. This removes AppArmor confinement for this container only.

Both lines are commented out in `docker-compose.yml`.

## Local AI with Ollama (optional)

Apps that write text can use models running on this machine instead of a paid API. `docker-compose.yml` has an `ollama` service that only starts with its profile:

```bash
docker compose -f docker/docker-compose.yml --profile ollama up -d
docker exec ollama ollama pull llama3.2      # download a model (about 2 GB)
```

Then in Settings > AI providers, tick "Use it" under Ollama (the address is already set to the `ollama` container), and pick Ollama in each app's settings. The model field takes any model you have pulled; empty means `llama3.2`.

- Models are kept in the `ollama-models` volume.
- It runs on the CPU. On a Raspberry Pi use small models (`llama3.2:1b`, `qwen2.5:1.5b`): a short text takes about a minute, which is fine for a scheduled print.

## Apps from a local folder (development)

Mount a checkout of [theticketpost-apps](https://github.com/theticketpost/theticketpost-apps) on `/data/apps`:

```bash
-v /path/to/theticketpost-apps:/data/apps
```

Uninstalling an app from the UI deletes its folder, also in a mounted checkout.
