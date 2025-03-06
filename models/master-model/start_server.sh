#!/bin/sh

export MLOPS_KAFKA_REQUEST_TIMEOUT_MS=60000
export MLOPS_KAFKA_BOOTSTRAP_SERVERS="bhinks.servicebus.windows.net:9093"
export MLOPS_KAFKA_SASL_MECHANISM="PLAIN"
export MLOPS_KAFKA_TOPIC_NAME="bhinks-agent-topic"
export MLOPS_KAFKA_SECURITY_PROTOCOL="SASL_SSL"
export MLOPS_KAFKA_SASL_JAAS_CONFIG='org.apache.kafka.common.security.plain.PlainLoginModule required username="$ConnectionString" password="Endpoint= sb://bhinks.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=HCuF2xyAOzDRK/rmUwPgELHNgmhUcNV7gSrdG2sit1s=";'
export MLOPS_SPOOLER_TYPE="KAFKA"
export MLOPS_KAFKA_SESSION_TIMEOUT_MS=30000
export MLOPS_KAFKA_SASL_PASSWORD='Endpoint= sb://bhinks.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=HCuF2xyAOzDRK/rmUwPgELHNgmhUcNV7gSrdG2sit1s='
export MLOPS_KAFKA_SASL_USERNAME='$ConnectionString'

echo "Starting Custom Model environment with DRUM prediction server"

if [ "${ENABLE_CUSTOM_MODEL_RUNTIME_ENV_DUMP}" = 1 ]; then
    echo "Environment variables:"
    env
fi

echo
echo "Executing command: drum server $*"
echo
exec drum server "$@"