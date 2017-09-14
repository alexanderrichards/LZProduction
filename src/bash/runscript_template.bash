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

## Simulation
###########################
{% if app_version %}
{% include "Simulation.template" %}
{% endif %}

## Reduction
###########################
{% if reduction_version %}
{% include "Reduction.template" %}
{% endif %}

## DER
###########################
{% if der_version %}
{% include "DER.template" %}
{% endif %}

## LZap
###########################
{% if lzap_version %}
{% include "LZap.template" %}
{% endif %}

## Upload
###########################
{% include "Upload.template" %}
