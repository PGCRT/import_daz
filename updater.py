# SPDX-FileCopyrightText: 2016-2026, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import shutil
import tempfile
import urllib.request
import zipfile

import bpy

from .buildnumber import BUILD

REPO = "Diffeomorphic/import_daz"
BRANCH = "master"
BUILD_URL = "https://raw.githubusercontent.com/%s/%s/buildnumber.py" % (REPO, BRANCH)
ZIP_URL = "https://github.com/%s/archive/refs/heads/%s.zip" % (REPO, BRANCH)

STATUS_UNKNOWN = "UNKNOWN"
STATUS_CHECKING = "CHECKING"
STATUS_CURRENT = "CURRENT"
STATUS_OUTDATED = "OUTDATED"
STATUS_ERROR = "ERROR"
STATUS_UPDATED = "UPDATED"

status = STATUS_UNKNOWN
message = "Update status unknown"
remoteBuild = None
errorMessage = ""


def getRemoteBuild():
    with urllib.request.urlopen(BUILD_URL, timeout=10) as fp:
        text = fp.read().decode("utf-8")
    match = re.search(r"BUILD\s*=\s*(\d+)", text)
    if not match:
        raise RuntimeError("Could not read remote build number")
    return int(match.group(1))


def checkForUpdate():
    global status, message, remoteBuild, errorMessage
    status = STATUS_CHECKING
    message = "Checking for updates"
    errorMessage = ""
    try:
        remoteBuild = getRemoteBuild()
    except Exception as err:
        status = STATUS_ERROR
        errorMessage = str(err)
        message = "Update check failed"
    else:
        if remoteBuild > BUILD:
            status = STATUS_OUTDATED
            message = "Update available: build %d" % remoteBuild
        else:
            status = STATUS_CURRENT
            message = "Up to date: build %d" % BUILD


def startupCheck():
    checkForUpdate()
    return None


def getStatusLabel():
    if status == STATUS_CURRENT:
        return message, 'CHECKMARK'
    elif status == STATUS_OUTDATED:
        return message, 'ERROR'
    elif status == STATUS_ERROR:
        return message, 'CANCEL'
    elif status == STATUS_UPDATED:
        return message, 'CHECKMARK'
    elif status == STATUS_CHECKING:
        return message, 'TIME'
    else:
        return message, 'QUESTION'


def updateAddon():
    global status, message, remoteBuild
    if remoteBuild is None:
        checkForUpdate()
    if status == STATUS_CURRENT:
        return "DAZ Importer is already up to date"
    if status == STATUS_ERROR:
        raise RuntimeError(errorMessage or message)

    addonDir = os.path.dirname(__file__)
    with tempfile.TemporaryDirectory() as tmpdir:
        zippath = os.path.join(tmpdir, "import_daz.zip")
        urllib.request.urlretrieve(ZIP_URL, zippath)
        with zipfile.ZipFile(zippath, "r") as zfile:
            zfile.extractall(tmpdir)
        roots = [path for path in os.listdir(tmpdir) if path.startswith("import_daz-")]
        if not roots:
            raise RuntimeError("Downloaded archive did not contain the addon")
        srcDir = os.path.join(tmpdir, roots[0])
        for name in os.listdir(srcDir):
            if name in {".git", "__pycache__"}:
                continue
            src = os.path.join(srcDir, name)
            dst = os.path.join(addonDir, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    status = STATUS_UPDATED
    if remoteBuild:
        message = "Updated to build %d; restart Blender" % remoteBuild
    else:
        message = "Updated; restart Blender"
    return message


class DAZ_OT_UpdateAddon(bpy.types.Operator):
    bl_idname = "daz.update_addon"
    bl_label = "Update"
    bl_description = "Update DAZ Importer from Diffeomorphic/import_daz on GitHub"

    def execute(self, context):
        try:
            msg = updateAddon()
        except Exception as err:
            self.report({'ERROR'}, str(err))
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


classes = [
    DAZ_OT_UpdateAddon,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.timers.register(startupCheck, first_interval=1.0)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
