#!/bin/bash
FILE_PATH="default"

PCAP_DIR 	= 	pcap
LOG_DIR 	= 	log


all: run

run: clean
	sudo PATH=$(PATH) PYTHONPATH=$(PYTHONPATH) python3 $(FILE_PATH)/FAT_INT/BMv2/example/network.py --p4 $(FILE_PATH)/FAT_INT/BMv2/p4src/fat_int.p4 --file_path $(FILE_PATH)

stop:
	sudo PATH=$(PATH) `which mn` -c

clean: stop
	sudo rm -f *.pcap
	# rm -rf $(PCAP_DIR) $(LOG_DIR) $(RULE_DIR)/rule*
	sudo rm -rf $(PCAP_DIR) $(LOG_DIR)