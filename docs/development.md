# Local development with minikube

## Prerequisites
- [minikube](https://kubernetes.io/docs/getting-started-guides/minikube/) v0.21.0
- [infraboxcli](https://github.com/infrabox/cli)
- [mc](https://docs.minio.io/docs/minio-client-quickstart-guide)
- [helm](https://github.com/kubernetes/helm)

## Docker registry
You may want to run you own docker registry where you can push to. Run this on your host:

    $ docker run -d -p 5000:5000 --restart always --name registry registry:2

Add the registry as insecure in /etc/docker/daemon.json

    { "insecure-registry": ["<YOUR_HOST>:5000"] }

Use the IP address of your host for <YOUR\_HOST> and not localhost or 127.0.0.1, because kubernetes needs to access it from within the minikube VM.
Restart the docker daemon.

    $ sudo service docker restart

Validate if everything works:

    $ docker pull alpine
    $ docker tag alpine <YOUR_HOST>:5000/alpine
    $ docker push <YOUR_HOST>:5000/alpine

## Start Minikube
Start minikube:

    $ minikube start \
        --insecure-registry <YOUR_HOST>:5000 \
        --cpus 4 \
        --memory 8192 \
        --disk-size 100gb \
        --kubernetes-version v1.6.4

## Install helm

Install helm

    $ helm init

## Build docker images

Build all images:

    $ ./deploy/build.sh <YOUR_HOST>:5000/

push them to your registry:

    $ ./deploy/push.sh <YOUR_HOST>:5000/

You may want to modifiy build.sh or push.sh to only build the images you modified.

## Deploy InfraBox
We have a default configuration for InfraBox in deploy/infrabox/values_minikube.yaml.template
Copy it to helm/infrabox/values_minikube.yaml and edit it.
Replace <YOUR_HOST> and <MINIKUBE_HOST> with the IP addresses of your host and the minikube vm respectively.

Do the same for postgres. Copy helm/infrabox/values_minikube.yam.template to lhelm/infrabox/values_minikube.yaml and edit it.

To install InfraBox run:

    $ cd deploy
    $ ./install.sh

You should now be able to access InfraBox under http://<MINIKUBE_HOST>:30201.

If you use infraboxcli make sure you always use the --host option:

    $ infrabox --host http://<MINIKUBE_HOST>:30200 ...

You can access the different components at:

- API: <MINIKUBE_HOST>:30200
- Dashboard: <MINIKUBE_HOST>:30201
- Docker Registry: <MINIKUBE_HOST>:30202
- Docs: <MINIKUBE_HOST>:30203

## Uninstall InfraBox

    $ cd deploy
    $ ./uninstall.sh

## Upgrade

    $ cd deploy/infrabox
    $ helm upgrade infrabox -f values_install.yaml .

