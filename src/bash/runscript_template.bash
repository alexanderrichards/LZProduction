#!/bin/bash
function stop_on_error {
    ${@:1:(($#-1))}
    ret=$?
    if [ $ret -ne 0 ]
    then
	echo ${@:$#} "exit code: $ret" >&2
	exit $ret
    fi
}

export OUTPUT_DIR=$(pwd)
SE={{ se }}

{% if app_version %}
## Simulation
###########################
{% include "Simulation.template" %}
{% endif %}

{% if reduction_version %}
## Reduction
###########################
{% include "Reduction.template" %}
{% endif %}

{% if der_version %}
## DER
###########################
{% include "DER.template" %}
{% endif %}

{% if lzap_version %}
## LZap
###########################
{% include "LZap.template" %}
{% endif %}

## Upload
###########################
{% include "Upload.template" %}
