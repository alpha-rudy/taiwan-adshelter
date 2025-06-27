MAP_NAME := NPA_Taiwan_ADShelter

ROOT_DIR := $(shell pwd)
BUILD_DIR := $(ROOT_DIR)/build
TOOLS_DIR := $(ROOT_DIR)/tools
JAVACMD_OPTIONS ?= -Xmx68G -server -Dfile.encoding=UTF-8
OSMOSIS_CMD := $(TOOLS_DIR)/osmosis-0.48.3/bin/osmosis
ZIP_CMD := 7z a -tzip -mx=6
MAPWITER_THREADS = 8
TAIWAN_BBOX=21.55682,118.12141,26.44212,122.31377
VERSION := $(shell date +%Y.%m.%d)

# remove half-done files on error
.DELETE_ON_ERROR:
# keep intermediate files
.SECONDARY:

.PHONY: all
all: $(BUILD_DIR)/$(MAP_NAME).zip

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)

.PHONY: osm
osm: $(BUILD_DIR)/$(MAP_NAME).osm
$(BUILD_DIR)/$(MAP_NAME).osm: tools/convert_kml_to_osm.py srcs/*.kml
	mkdir -p $(BUILD_DIR)
	python3 tools/convert_kml_to_osm.py --start-id -1000 srcs/ $(BUILD_DIR)/$(MAP_NAME).osm

.PHONY: ren
ren: $(BUILD_DIR)/$(MAP_NAME)-ren.pbf
%-ren.pbf: %.osm
	osmium renumber \
		-s 20000000000,0,0 \
		$< \
		-Oo $@

.PHONY: map
map: $(BUILD_DIR)/$(MAP_NAME).map
%.map: %-ren.pbf
	export JAVACMD_OPTIONS="$(JAVACMD_OPTIONS)" && \
	sh $(OSMOSIS_CMD) \
		--read-pbf "$<" \
		--buffer \
		--mapfile-writer \
			type=ram \
			threads=$(MAPWITER_THREADS) \
			bbox=$(TAIWAN_BBOX) \
			preferred-languages="zh,en" \
			tag-conf-file=confs/ads-mapping.xml \
			polygon-clipping=true way-clipping=true label-position=true \
			zoom-interval-conf=6,0,6,10,7,11,14,12,21 \
			map-start-zoom=12 \
			comment="台灣防空避難處所 $(VERSION)" \
			file="$@"
.PHONY: poi
poi: $(BUILD_DIR)/$(MAP_NAME).poi
$(BUILD_DIR)/$(MAP_NAME).poi: $(BUILD_DIR)/$(MAP_NAME)-ren.pbf
%.poi: %-ren.pbf
	export JAVACMD_OPTIONS="-server" && \
		sh $(OSMOSIS_CMD) \
			--rb file="$<" \
			--poi-writer \
			all-tags=true \
			geo-tags=true \
			names=false \
			bbox=$(TAIWAN_BBOX) \
			ways=true \
			tag-conf-file="confs/poi-mapping.xml" \
			comment="台灣防空避難離線地圖 $(VERSION)" \
			file="$@"

.PHONY: zip
zip: $(BUILD_DIR)/$(MAP_NAME).zip
$(BUILD_DIR)/$(MAP_NAME).zip: $(BUILD_DIR)/$(MAP_NAME).map $(BUILD_DIR)/$(MAP_NAME).poi
%.zip: %.map %.poi
	cd $(BUILD_DIR)/ && $(ZIP_CMD) $(shell basename $@) $$(ls *.map *.poi)

.PHONY: map.zip
map.zip: $(BUILD_DIR)/$(MAP_NAME).map.zip
$(BUILD_DIR)/$(MAP_NAME).map.zip: $(BUILD_DIR)/$(MAP_NAME).map
%.map.zip: %.map
	cd $(BUILD_DIR)/ && $(ZIP_CMD) $(shell basename $@) $$(ls *.map)
