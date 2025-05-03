# extract-subtitle
A python program to extract subtitles from a mp3 file.

## Getting started

### Create a new python env
```
python3.11 -m venv .venv
```

### Active the python env
```
source ./.venv/bin/activate.fish
```

### Install all dependencies
```
pip3 install -r requirements.txt
```

## Usage
To starting the process you just need run `main.py` file providing a mp3 file name:

```
python3.11 main.py --file [MP3_FILE]
```

By default the program will create a `.srt` at your home directory, you can override all default settings using command line arguments. 

```
python3.11 main.py --help
```

You'll see all argument options

### Updating requirements.txt
To update the `requirements.txt` with all new dependencies run:

```
pip freeze > requirements.txt
```
