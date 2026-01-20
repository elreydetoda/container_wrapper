# Container Wrapper
The `container_wrapper` payload is a special payload. This is a OCI compliant container image (i.e. `.tar` file) that acts as a "wrapper" around another agent. As such, this payload type has no commands and no supported C2 profiles - it simply acts as a way to turn arbitrary other Linux agents into properly format container images and set them as the initial startup command.

This payload type is for Mythic 2.2.7 and reports as version "8". It is not compatible with Mythic version 2.1.

## Additional modification

```console
$ mv -v docker-compose.yml{,.orig00}
# https://chatgpt.com/share/696fa368-5a04-8005-ab5a-4673b140fb48
$ cat docker-compose.yml.orig00 | yq '
  .services.container_wrapper.environment |=
    ((. // []) + [
      "STORAGE_DRIVER=vfs",
      "BUILDAH_ISOLATION=chroot",
      "_CONTAINERS_USERNS_CONFIGURED=1"
    ] | unique)
  |
  .services.container_wrapper.security_opt |=
    ((. // []) + ["no-new-privileges:true"] | unique)
  |
  .services.container_wrapper.tmpfs |=
    ((. // []) + ["/tmp", "/run"] | unique)
  |
  .services.container_wrapper.pids_limit = 256
' > docker-compose.yml
# https://chatgpt.com/share/696fa24f-6944-8005-b364-aecc69de9ef2
$ diff docker-compose.yml{,.orig00}
151,153d150
<             - STORAGE_DRIVER=vfs
<             - BUILDAH_ISOLATION=chroot
<             - _CONTAINERS_USERNS_CONFIGURED=1
174,179d170
<         security_opt:
<           - no-new-privileges:true
<         tmpfs:
<           - /tmp
<           - /run
<         pids_limit: 256
$ docker compose down container_wrapper && sleep 3 && docker compose up container_wrapper -d
```

### Poseidon specific

Till a PR is merged for Poseidon to allow this payload wrapper to wrap it, you'll also need to modify your poseidon agent's code, re-build the image, & deploy it with that new version.

```console
$ cd /opt/mythic/InstalledServices/poseidon
$ cp -v poseidon/agentfunctions/builder.go{,.orig00}
'poseidon/agentfunctions/builder.go' -> 'poseidon/agentfunctions/builder.go.orig00'
$ vim poseidon/agentfunctions/builder.go
$ diff poseidon/agentfunctions/builder.go{,.orig00}
43c43
<       CanBeWrappedByTheFollowingPayloadTypes: []string{"container_wrapper"},
---
>       CanBeWrappedByTheFollowingPayloadTypes: []string{},
$ docker build . -t ghcr.io/mythicagents/poseidon:v0.0.3.9-alpha
$ cd /opt/mythic/
$ vim docker-compose.yml
# add new image to replace: image: ghcr.io/mythicagents/poseidon:v0.0.3.9 -> image: ghcr.io/mythicagents/poseidon:v0.0.3.9-alpha
$ docker compose down poseidon && sleep 3 && docker compose up poseidon -d
```

## How to install an agent in this format within Mythic

When it's time for you to test out your install or for another user to install your agent, it's pretty simple. Within Mythic you can run the `mythic-cli` binary to install this in one of three ways:

* `sudo ./mythic-cli install github https://github.com/user/repo` to install the main branch
* `sudo ./mythic-cli install github https://github.com/user/repo branchname` to install a specific branch of that repo
* `sudo ./mythic-cli install folder /path/to/local/folder/cloned/from/github` to install from an already cloned down version of an agent repo

Now, you might be wondering _when_ should you or a user do this to properly add your agent to their Mythic instance. There's no wrong answer here, just depends on your preference. The three options are:

* Mythic is already up and going, then you can run the install script and just direct that agent's containers to start (i.e. `sudo ./mythic-cli payload start agentName` and if that agent has its own special C2 containers, you'll need to start them too via `sudo ./mythic-cli c2 start c2profileName`).
* Mythic is already up and going, but you want to minimize your steps, you can just install the agent and run `sudo ./mythic-cli mythic start`. That script will first _stop_ all of your containers, then start everything back up again. This will also bring in the new agent you just installed.
* Mythic isn't running, you can install the script and just run `sudo ./mythic-cli mythic start`. 

## Icon

https://www.flaticon.com/free-icon/sweet_3050124

<a href="https://www.flaticon.com/free-icons/sugar" title="sugar icons">Sugar icons created by Freepik - Flaticon</a>
