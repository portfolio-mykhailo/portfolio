#!/bin/bash

IMAGE_NAME="<image_name>"
CONTAINER_NAME="<container_name>"

PROJECT_PATH="<path>"

# delete current container and create new
if [ "$(docker ps -aq -f name=^/$CONTAINER_NAME$)" ]; then
    docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME
    docker rmi -f $IMAGE_NAME
fi

docker build -t $IMAGE_NAME .

docker run --name $CONTAINER_NAME -v $PROJECT_PATH:/app -d $IMAGE_NAME && docker logs -f $CONTAINER_NAME
