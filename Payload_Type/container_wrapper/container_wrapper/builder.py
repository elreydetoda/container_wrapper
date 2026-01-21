from mythic_container.PayloadBuilder import *
from mythic_container.MythicCommandBase import *
import asyncio
import os
import tempfile
from distutils.dir_util import copy_tree
from pathlib import PurePath, Path
import base64
from mythic_container.MythicRPC import *


class ContainerWrapper(PayloadType):

    name = "container_wrapper"
    file_extension = "tar"
    author = "@elreydetoda"
    supported_os = [SupportedOS.Linux]
    wrapper = True
    wrapped_payloads = ["poseidon"]
    note = "This is a wrapper payload that takes in a Linux executable payload and generates a docker container file (i.e. a tar file)."
    supports_dynamic_loading = False
    build_parameters = [
        BuildParameter(
            name="base_image",
            parameter_type=BuildParameterType.String,
            description="Choose a base container image (e.g. docker.io/ubuntu:24.04 OR scratch)",
            default_value="docker.io/ubuntu:24.04"
        ),
        BuildParameter(
            name="entrypoint_file_name",
            parameter_type=BuildParameterType.String,
            default_value="entrypoint",
            description="Binary that will be run when the container starts up",
        ),
        BuildParameter(
            name="container_image_name",
            parameter_type=BuildParameterType.String,
            default_value="oci_container_image",
            description="The name of the container image you want to export",
        ),
        BuildParameter(
            name="container_image_version",
            parameter_type=BuildParameterType.String,
            default_value="latest",
            description="The version of the container image you want to export",
        )
    ]
    c2_profiles = []
    agent_path = PurePath(".") / "container_wrapper"
    agent_icon_path = agent_path / "container_wrapper.svg"
    agent_code_path = agent_path / "agent_code"
    build_steps = [
        BuildStep(step_name="Writing Payload", step_description="Writing payload to temp location"),
        BuildStep(step_name="Building", step_description="Compiling with nuget and msbuild")
    ]


    async def build(self) -> BuildResponse:
        # this function gets called to create an instance of your payload
        resp = BuildResponse(status=BuildStatus.Error)
        output = ""
        try:
            with tempfile.TemporaryDirectory(suffix=self.uuid) as tmpdir:
                # agent_build_path = tempfile.TemporaryDirectory(suffix=self.uuid).name
                agent_build_path = tmpdir
                # write payload as the "entrypoint" binary, so the name isn't obvious
                payload_bin = Path(agent_build_path, self.get_parameter("entrypoint_file_name"))
                payload_bin.write_bytes(self.wrapped_payload)
                await SendMythicRPCPayloadUpdatebuildStep(MythicRPCPayloadUpdateBuildStepMessage(
                    PayloadUUID=self.uuid,
                    StepName="Writing Payload",
                    StepStdout="Wrote payload file",
                    StepSuccess=True
                ))
                command = [
                    # adding isolation=chroot because running in a container: https://github.com/containers/buildah/issues/1901#issuecomment-539499449
                    f"newcontainer=$(buildah from --isolation=chroot {self.get_parameter('base_image')})",
                    f"chmod +x {payload_bin}",
                    f"buildah add $newcontainer {payload_bin}",
                    f"buildah config --cmd /{payload_bin.name} $newcontainer",
                    f"buildah commit $newcontainer {self.get_parameter('container_image_name')}:latest",
                    "buildah push " + 
                        f"{self.get_parameter('container_image_name')}:{self.get_parameter('container_image_version')} " +
                        f"oci-archive:{Path(agent_build_path, str(self.get_parameter('container_image_name')) + '.tar')}:{self.get_parameter('container_image_version')}",
                    # "buildah rm $newcontainer",
                    # f"buildah rmi {self.get_parameter('container_image_name')}:{self.get_parameter('container_image_version')}"
                ]
                proc = await asyncio.create_subprocess_shell(
                    " && ".join(command),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=agent_build_path,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    output += f"[stdout]\n{stdout.decode()}"
                if stderr:
                    output += f"[stderr]\n{stderr.decode()}"
                # output_path = (
                #     PurePath(agent_build_path)
                #     / "WindowsService1"
                #     / "bin"
                #     / "Release"
                #     / "WindowsService1.exe"
                # )
                # output_path = str(output_path)
                output_path = Path(agent_build_path, str(self.get_parameter('container_image_name')) + '.tar')
                if os.path.exists(output_path):
                    resp.payload = output_path.read_bytes()
                    resp.status = BuildStatus.Success
                    resp.build_message = f"{stdout=}\n{stderr=}"
                else:
                    resp.payload = b""
                    resp.build_stderr = output + "\n" + str(output_path)
        except Exception as e:
            raise Exception(str(e) + "\n" + output)
        return resp
