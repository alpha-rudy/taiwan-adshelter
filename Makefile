ROOT_DIR := $(shell pwd)
TOOLS_DIR := $(ROOT_DIR)/tools
JAVACMD_OPTIONS ?= -Xmx68G -server -Dfile.encoding=UTF-8
OSMOSIS_CMD := $(TOOLS_DIR)/osmosis-0.48.3/bin/osmosis
ZIP_CMD := 7z a -tzip -mx=6
MAPWITER_THREADS = 8
TAIWAN_BBOX=21.55682,118.12141,26.44212,122.31377
VERSION := $(shell date +%Y.%m.%d)

.PHONY: all
all: build/NPA_Taiwan_AirDS.map.zip

.PHONY: clean
clean:
	rm -rf build

build/taiwan_ads.osm: tools/convert_kml_to_osm.py srcs/*.kml
	mkdir -p build
	python3 tools/convert_kml_to_osm.py --start-id -1000 srcs/ build/taiwan_ads.osm

build/NPA_Taiwan_AirDS.map: build/taiwan_ads.osm
	osmium renumber \
		-s 1,1,0 \
		$< \
		-Oo $<.pbf
	export JAVACMD_OPTIONS="$(JAVACMD_OPTIONS)" && \
	sh $(OSMOSIS_CMD) \
		--read-pbf $<.pbf \
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

build/NPA_Taiwan_AirDS.map.zip: build/NPA_Taiwan_AirDS.map
	cd build/ && $(ZIP_CMD) $(shell basename $@) $(shell basename $<)
