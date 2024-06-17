# 定义变量
APP_NAME = kazu
SOURCE = src/kazu/__main__.py
ICON = assets/Ka.ico
DIST_DIR = dist
SPEC_FILE = $(APP_NAME).spec

# 编译规则
all: build

build:
	@echo "Start building $(APP_NAME)..."
	pyinstaller --name=$(APP_NAME) \
	              --onefile \
	              --distpath=$(DIST_DIR) \
	              --collect-binaries pyapriltags \
	              --collect-binaries pyuptech \
	              --collect-binaries opencv-python-headless \
	              --icon=$(ICON) \
	              $(SOURCE)
	@echo "$(APP_NAME) was successfully built! See $(DIST_DIR)/$(APP_NAME)"

clean:
	@echo "Start cleaning..."
	rm -rf $(DIST_DIR) $(SPEC_FILE)
	@echo "$(APP_NAME) was successfully cleaned!"

rebuild: clean all
	@echo "$(APP_NAME) was successfully rebuilt!"

.PHONY: clean rebuild build