#!/bin/bash

python3 make_config_macros.py

for i in *.csv; do
    python3 translate.py $i ../../translate/
done

rm ../base.cfg.tmp
