#!/usr/bin/env bash
set -e

context_dir="./context"
dockerfile="s2downloader_ci.docker"
python_script='
version = {}
with open("../../s2downloader/version.py") as version_file:
    exec(version_file.read(), version)
print(version["__version__"])
'
version=`python -c "$python_script"`
runner_version="v$version"
runner_tag="s2downloader_ci:$runner_version"
gitlab_runner="s2downloader_ci_gitlab_ci_runner_$runner_version"

echo "#### Build runner docker image"
if [[ "$(docker images ${runner_tag} | grep ${runner_tag} 2> /dev/null)" != "" ]]; then
  docker rmi ${runner_tag}
fi
docker build --network=host -f ${context_dir}/${dockerfile} -m 20G -t ${runner_tag} ${context_dir}

# create the gitlab-runner docker container for the current project
# Remove packages
rm -fr context/s2downloader

echo "#### Create gitlab-runner (daemon) container"
if [ "$(docker ps -qa -f name=${gitlab_runner})" ]; then
    if [ "$(docker ps -q -f name=${gitlab_runner})" ]; then
        docker stop ${gitlab_runner};
    fi
    docker rm ${gitlab_runner};
fi
docker run -d --name ${gitlab_runner} --network host --restart always -v /var/run/docker.sock:/var/run/docker.sock gitlab/gitlab-runner:latest

echo "#### Register container at gitlab"
# register the runner at the corresponding GitLab repository via a registration-token
# NOTE: In case of locally stored images (like here), the docker pull policy 'never' must be used
#       (see https://docs.gitlab.com/runner/executors/docker.html#how-pull-policies-work).
read -p "Please enter gitlab token: " token
echo ""

url='https://git.gfz-potsdam.de'

cmd="gitlab-runner --debug register \
        --executor 'docker' \
        --docker-image '${runner_tag}' \
        --url '${url}' \
        --token '${token}' \
        --description '${gitlab_runner}' \
        --docker-pull-policy='never'
"
echo "Running the following command:"
echo "${cmd}"
docker exec -it ${gitlab_runner} /bin/bash -c "${cmd}"
echo 'Done'
echo 'NOTE: If the runner stays inactive, re-create the runner and register it again.'
