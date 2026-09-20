"""Exercise the local sandbox through real HTTP. Refuses non-loopback URLs."""

import argparse
import json
import random
import re
import struct
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import zlib


def local_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("This smoke test only writes to an HTTP loopback sandbox.")
    return url


def photo_fixture():
    """A real, synthetic PNG; no gallery files or personal images."""
    def chunk(kind, payload):
        return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload))
    rng = random.Random(7)
    raw = b"".join(b"\x00"+rng.randbytes(48*3) for _ in range(48))
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",48,48,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b"")


def run(base):
    base = local_url(base).rstrip("/")
    def call(path, body=None, expected=200):
        label = path.split('?')[0]
        print(('GET' if body is None else 'POST')+' '+label, flush=True)
        request = Request(base+path, data=None if body is None else json.dumps(body).encode(),
                          headers={"Content-Type":"application/json"})
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            status, payload = response.status, response.read()
        assert status==expected,(path,status,payload[:120])
        return json.loads(payload)

    health = call("/health")
    assert health["environment"]=="local-demo", "Refusing to write to a non-sandbox API"
    assert health["ward_index"]=={"loaded":True,"wards":289}
    assert health["drafting"]["mode"]=="template" and health["delivery_mode"]=="DEMO_OUTBOX"
    ward = call("/wards/lookup?"+urlencode({"lat":28.6315,"lng":77.2167}))
    assert ward["ward_id"]
    call("/leaderboard")
    photo = photo_fixture()
    signed = call("/complaints/presign",{"content_type":"image/png","content_length":len(photo)})
    upload = Request(local_url(signed["upload_url"]), data=photo, method="PUT",headers=signed["required_headers"])
    with urlopen(upload,timeout=10) as response:
        assert response.status==200
    created = call("/complaints",{"photo_key":signed["photo_key"],"issue_type":"POTHOLE",
        "description":"Synthetic local report: the road surface needs repair at the demo crossing.",
        "lat":28.6315,"lng":77.2167,"reporter_email":"smoke@example.com"},expected=202)
    identifier, token = created["complaint_id"], created["status_token"]
    assert created["queued"] is True
    end = time.monotonic()+15
    while True:
        detail = call("/complaints/"+identifier)
        if detail["draft_status"]=="DRAFTED":
            break
        assert time.monotonic()<end,"Local queue worker did not finish"
        time.sleep(0.1)
    assert detail["is_demo"] is True and detail["draft_source"]=="template"
    assert detail["body_en"] and re.search(r"[\u0900-\u097f]",detail["body_hi"])
    public = json.dumps(detail)+json.dumps(call("/complaints"))
    assert token not in public and "smoke@example.com" not in public
    assert "status_token" not in public and "reporter_email" not in public
    with urlopen(local_url(detail["photo_url"]),timeout=10) as response:
        assert response.read()==photo
    call(f"/complaints/{identifier}/status",{"token":"wrong","action":"resolve"},expected=403)
    result = call(f"/complaints/{identifier}/status",{"token":token,"action":"resolve"})
    assert result["status"]=="RESOLVED"
    result = call(f"/complaints/{identifier}/status",{"token":token,"action":"reopen"})
    assert result["status"]=="OPEN" and not result.get("resolved_at")
    print("Local HTTP smoke passed: ward lookup, leaderboard, real PNG upload/download, queued bilingual draft, private projections, rejected wrong token, resolve and reopen.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://localhost:8101")
    run(parser.parse_args().url)
