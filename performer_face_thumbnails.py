import os
import sys
import json
import requests
import urllib3
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import log
import face_recognition
import numpy as np


def main():
    input = None

    if len(sys.argv) < 2:
        input = readJSONInput()
        log.LogDebug("Raw input: %s" % json.dumps(input))
    else:
        log.LogDebug("Using command line inputs")
        mode = sys.argv[1]
        log.LogDebug("Command line inputs: {}".format(sys.argv[1:]))

        input = {}
        input["args"] = {"mode": mode}
        # just some hard-coded values
        input["server_connection"] = {
            "Scheme": "http",
            "Port": 9999,
        }

    output = {}
    run(input, output)

    out = json.dumps(output)
    print(out + "\n")


def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)


def run(input, output):
    modeArg = input["args"]["mode"]
    try:
        if modeArg == "" or modeArg == "create":
            client = StashInterface(input["server_connection"])
            sceneThumbnail(client)
    except Exception as e:
        raise

    output["output"] = "ok"


def sceneThumbnail(client):
    scenes = client.listScenes()
    generate_path = client.getConfigPath()
    vtt_path = os.path.join(generate_path, "vtt")

    for scene in scenes:
        log.LogInfo(scene["id"])
        image = os.path.join(vtt_path, "{}_sprite.jpg".format(scene["oshash"]))
        vtt = os.path.join(vtt_path, "{}_thumbs.vtt".format(scene["oshash"]))
        if os.path.exists(image) and os.path.exists(vtt):
            sprite = Image.open(image)
            left = top = right = bottom = None
            time_offset = 0
            max_size = 0
            best_offset = 0
            for line in open(vtt).readlines():
                if "-->" in line:
                    tt = line.split("-->")[0]
                    hh, mm, ss = tt.split(":")
                    ss = ss.split(".")[0]
                    time_offset = int(ss) + int(mm) * 60 + int(hh) * 3600

                elif "xywh=" in line:
                    left, top, right, bottom = line.split("xywh=")[-1].split(",")
                    left, top, right, bottom = (
                        int(left),
                        int(top),
                        int(right),
                        int(bottom),
                    )
                else:
                    continue

                if not left:
                    continue

                cut_frame = sprite.crop((left, top, left + right, top + bottom))
                check_for_face = np.array(cut_frame)
                result = face_recognition.face_locations(check_for_face)
                if result:
                    new_size = sum(result[0])
                    if new_size > max_size:
                        best_offset = time_offset

            log.LogInfo(str(best_offset))
            query = """mutation{
sceneGenerateScreenshot(id: %s, at: %s)
}"""
            q = query % (scene["id"], best_offset)
            client._callGraphQL(q)


def tc_to_frame(hh, mm, ss, ff):
    return


#####################
#  Stash interface class
#####################


class StashInterface:
    url = ""
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1",
    }

    def __init__(self, conn):
        self._conn = conn
        self.ignore_ssl_warnings = True
        self.server = conn["Scheme"] + "://localhost:" + str(conn["Port"])
        self.url = self.server + "/graphql"
        self.auth_token = None
        if "SessionCookie" in self._conn:
            self.auth_token = self._conn["SessionCookie"]["Value"]

    def _callGraphQL(self, query, variables=None):
        json = {}
        json["query"] = query
        if variables != None:
            json["variables"] = variables

        if self.auth_token:
            response = requests.post(
                self.url,
                json=json,
                headers=self.headers,
                cookies={"session": self.auth_token},
                verify=not self.ignore_ssl_warnings,
            )
        else:
            response = requests.post(
                self.url,
                json=json,
                headers=self.headers,
                verify=not self.ignore_ssl_warnings,
            )

        if response.status_code == 200:
            result = response.json()
            if result.get("error", None):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data", None):
                return result.get("data")
        else:
            raise Exception(
                "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
                    response.status_code, response.content, query, variables
                )
            )

    def listScenes(self):
        query = """
query {
  findScenes(
    scene_filter: { organized: false, stash_id: {modifier: IS_NULL, value:""},  is_missing: "url" }
    filter: { per_page: -1 }
  ) {
    scenes {
      id
      oshash
      url
    }
  }
}

"""
        result = self._callGraphQL(query)
        # Assume that if a person has a url they will have grabbed the OG thumbnail. Ignore it
        scenes = [s for s in result["findScenes"]["scenes"] if not s["url"]]
        return scenes

    def createThumbnail(self, id, seconds):
        query = """mutation{
    sceneGenerateScreenshot(id: %s, at: %s)
}"""
        q = query % (id, seconds)
        log.LogInfo(q)
        return self._callGraphQL(q)

    def getConfigPath(self):
        query = """{
    configuration{
        general{
            generatedPath
        }
    }
}
"""
        result = self._callGraphQL(query)
        return result["configuration"]["general"]["generatedPath"]


main()
