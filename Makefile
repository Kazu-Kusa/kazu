# 定义变量
APP_NAME = kazu
SOURCE = src/kazu/__main__.py
ICON = assets/Ka.ico
DIST_DIR = dist
SPEC_FILE = $(APP_NAME).spec

# 编译规则
all: build_bin build_whl build_bin_ntk

build_bin_ntk:
	@echo "Start building Binary $(APP_NAME) with Nuitka..."
	nuitka --standalone \
	        --onefile \
	        --output-dir=$(DIST_DIR) \
	        --assume-yes-for-downloads \
	        --windows-icon-from-ico=$(ICON) \
	        --onefile-no-compression \
	        $(SOURCE)

build_bin:
	@echo "Start building Binary $(APP_NAME)..."
	pyinstaller --name=$(APP_NAME) \
	              --onefile \
	              --distpath=$(DIST_DIR) \
	              --collect-binaries pyapriltags \
	              --collect-binaries pyuptech \
	              --collect-binaries opencv-python-headless \
	              --icon=$(ICON) \
	              $(SOURCE)
	@echo "$(APP_NAME) was successfully built! See $(DIST_DIR)/$(APP_NAME)"

build_whl:
	@echo "Start building whl $(APP_NAME)..."
	pdm build -d $(DIST_DIR) --no-clean

	@echo "$(APP_NAME) was successfully built! See $(DIST_DIR)"

clean:
	@echo "Start cleaning..."
	rm -rf $(DIST_DIR) $(SPEC_FILE)
	@echo "$(APP_NAME) was successfully cleaned!"

rebuild: clean all
	@echo "$(APP_NAME) was successfully rebuilt!"

.PHONY: clean rebuild build_bin build_whl build_bin_ntk