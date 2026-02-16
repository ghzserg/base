#!/bin/bash

python3 make_config_macros.py

for i in *.csv; do
    python3 translate.py $i ../../translate/
done

rm ../ff5m_config_native.cfg
rm ../ff5m_config_off.cfg
rm ../ad5x_config_native.cfg
rm ../ad5x_config_off.cfg
