#!/bin/bash
cd smart-py
~/smartpy-cli/SmartPy.sh test objkt_swap_v2_test.py /tmp/objkt_swap_test
~/smartpy-cli/SmartPy.sh test objkt_swap_v3_test.py /tmp/objkt_swap_test
cd - > /dev/null
