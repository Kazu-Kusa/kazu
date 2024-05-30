# 定义变量
APP_NAME = kazu
SOURCE = src\kazu\__main__.py
ICON = assets\Ka.ico
DIST_DIR = dist
SPEC_FILE = $(APP_NAME).spec

# 编译规则
all: $(DIST_DIR)/$(APP_NAME)

$(DIST_DIR)/$(APP_NAME): $(SOURCE)
	@echo "Start building $(APP_NAME)..."
	pyinstaller --name=$(APP_NAME) \
	              --onefile \
	              --noconsole \
	              --distpath=$(DIST_DIR) \
	              --collect-binaries pyapriltags \
	              --collect-binaries pyuptech \
	              --collect-binaries opencv-python-headless \
	              $(if $(ICON),--icon=$(ICON)) \
	              $(SOURCE)
	@echo "$(APP_NAME) was successfully built! See $(DIST_DIR)/$(APP_NAME)"

clean:
	@echo "Start cleaning..."
	rm -rf $(DIST_DIR) $(SPEC_FILE)
	@echo "$(APP_NAME) was successfully cleaned!"

rebuild: clean all
	@echo "$(APP_NAME) was successfully rebuilt!"

.PHONY: clean rebuild