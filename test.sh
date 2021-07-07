#!/bin/bash
cd smart-py
~/smartpy-cli/SmartPy.sh test objkt_swap_tests.py /tmp/objkt_swap_test
~/smartpy-cli/SmartPy.sh test marketplace_tests.py /tmp/objkt_swap_test
cd - > /dev/null
