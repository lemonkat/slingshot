PYTHON ?= python3.12
VENV_DIR = .venv

# OS Detection and path separators
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    ADD_DATA_SEP := ;
    VENV_BIN := $(VENV_DIR)/Scripts
else
    DETECTED_OS := $(shell uname -s)
    ADD_DATA_SEP := :
    VENV_BIN := $(VENV_DIR)/bin
endif

PIP = $(VENV_BIN)/pip
PYINSTALLER = $(VENV_BIN)/pyinstaller

.PHONY: all venv assets build package clean

all: package

$(VENV_DIR)/touchfile:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install numpy urwid pygame pyinstaller
	touch $(VENV_DIR)/touchfile

venv: $(VENV_DIR)/touchfile

assets/unscii-16-full.ttf:
	mkdir -p assets
	curl -L -o assets/unscii-16-full.ttf https://viznut.fi/unscii/unscii-16-full.ttf

assets: assets/unscii-16-full.ttf

build: venv assets
	$(PYINSTALLER) --windowed --collect-all urwid --add-data "assets/unscii-16-full.ttf$(ADD_DATA_SEP)assets" --name="Slingshot" game.py

package: build
ifeq ($(DETECTED_OS),Darwin)
	hdiutil create -volname "Slingshot" -srcfolder dist/Slingshot.app -ov -format UDZO dist/Slingshot.dmg
else ifeq ($(DETECTED_OS),Windows)
	$(PYTHON) -c "import shutil; shutil.make_archive('dist/Slingshot', 'zip', 'dist', 'Slingshot')"
else
	tar -czvf dist/Slingshot-linux.tar.gz -C dist Slingshot
endif

clean:
	rm -rf $(VENV_DIR)
	rm -rf build dist Slingshot.spec
