#!/usr/bin/python3
import subprocess
import tempfile
import requests
import hashlib
import os.path

test_packages = [
    # fc25 native package
    ('https://ftp-stud.hs-esslingen.de/pub/Mirrors/archive.fedoraproject.org/fedora/linux/releases/25/Everything/x86_64/os/Packages/f/filesystem-3.2-37.fc24.x86_64.rpm',
     '78914cd2b9664e621832a66f6139e6f3b05ccacaf414d0e0efc56c0c7bc734c4'),
    # qubes package built with old rpm
    ('https://mirrors.edge.kernel.org/qubes/repo/yum/r4.0/current/dom0/fc25/rpm/i3-4.16-9.fc25.x86_64.rpm',
     '9022f7c9d42b35b42fd4e4dccce71f9674e3815714d606c64234857c0a0b3f32'),
    # qubes package built with new rpm
    ('https://mirrors.edge.kernel.org/qubes/repo/yum/r4.0/current/dom0/fc25/rpm/hawkey-0.6.4-3.1.fc25.x86_64.rpm',
     '56eeba77f42bec4b554a72eca31923451efcb515ba9239c27ff3bae1a679b69a'),
    # template package
    ('https://mirrors.edge.kernel.org/qubes/repo/yum/r4.0/templates-itl/rpm/qubes-template-fedora-32-minimal-4.0.6-202101091323.noarch.rpm',
     '51061fd6c283aade36d4a329000e3570421fc07c64bb77fa1ea7407202f7d12c'),
]


def run_tests():
    for url, expected_sha in test_packages:
        print(os.path.basename(url))
        with tempfile.NamedTemporaryFile() as rpmfile:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            sha = hashlib.sha256()
            for chunk in r.iter_content(chunk_size=None):
                rpmfile.write(chunk)
                sha.update(chunk)
            rpmfile.flush()
            # verify if we get expected file, to avoid false negatives
            assert sha.hexdigest() == expected_sha, \
                '{} != {}'.format(sha.hexdigest(), expected_sha)

            subprocess.run(['rpm', '-qpi', rpmfile.name], check=True)
            subprocess.run(['rpmkeys', '-Kv', rpmfile.name], check=True)


if __name__ == '__main__':
    run_tests()
