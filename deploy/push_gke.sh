#!/bin/bash -e

docker_registry=${1:-""}
image_tag=${2:-"latest"}
cmd_prefix=${3:-"gcloud docker"}

echo "Pusing images for "
echo "  registry: $docker_registry"
echo "  tag: $image_tag"

$cmd_prefix -- push ${docker_registry}infrabox/job-api:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/gerrit/trigger:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/gerrit/review:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/api:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/docs:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/job:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/dashboard:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/scheduler:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/clair/analyzer:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/clair/updater:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/docker-registry/auth:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/docker-registry/nginx:$image_tag
$cmd_prefix -- push ${docker_registry}infrabox/postgres:$image_tag
