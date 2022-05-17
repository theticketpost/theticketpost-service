# theticketpost-service

## How to install

```bash
# Virtual environment creation
$bash> python -m venv .theticketpost
$bash> source .theticketpost/bin/activate
$bash> pip install --upgrade pip

# Service installation
$bash> python3 setup.py install --record files.txt

# Service uninstallation
$bash> xargs rm -rf < files.txt
```



## How to run

```bash
$bash> theticketpost-service
```

Open a browser and navigates to `localhost:8080`

## Mockup

You can find the mockup [here](https://mydraft.cc/c9t85hh6j4edn171387g)

## pageres
```bash
$bash> npm install --global pageres-cli
$bash> pageres http://localhost:8080 1920x8000 --selector=div#newspaper --overwrite --filename=last_newspaper
```

[Pageres Github](https://github.com/sindresorhus/pageres-cli)
