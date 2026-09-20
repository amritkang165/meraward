import importlib.util
import os
from pathlib import Path


def test_local_configuration_replaces_inherited_cloud_settings(monkeypatch):
    path=Path(__file__).resolve().parents[1]/"local_demo.py"
    spec=importlib.util.spec_from_file_location("demo_safety",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # monkeypatch restores the whole environment after configure changes it.
    for key in list(os.environ):
        monkeypatch.setenv(key,os.environ[key])
    changed=["AWS_ENDPOINT_URL","AWS_IGNORE_CONFIGURED_ENDPOINT_URLS","AWS_CONFIG_FILE",
             "AWS_SHARED_CREDENTIALS_FILE","AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY",
             "AWS_EC2_METADATA_DISABLED","AWS_DEFAULT_REGION","AWS_REGION","NO_PROXY",
             "COMPLAINTS_TABLE","WARDS_TABLE","RATE_LIMIT_TABLE","WARD_INDEX_NAME",
             "STATUS_INDEX_NAME","PHOTOS_BUCKET","DATA_BUCKET","WARDS_GEOJSON_PATH",
             "ALLOWED_ORIGIN","DELIVERY_MODE","SES_SENDER","SES_DEMO_RECIPIENT",
             "BEDROCK_ENABLED","BEDROCK_INFERENCE_PROFILE_ID","DRAFT_QUEUE_URL",
             "LOCAL_DEMO","REPORTS_PER_MINUTE","UPLOADS_PER_MINUTE","STATUS_UPDATES_PER_MINUTE"]
    for key in changed:
        monkeypatch.setenv(key,"inherited-test-value")
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3","https://s3.example")
    monkeypatch.setenv("AWS_PROFILE","inherited-profile")
    monkeypatch.setenv("AWS_SESSION_TOKEN","inherited-session")
    module.configure(5001,"http://localhost:5174")
    assert os.environ["AWS_ENDPOINT_URL"]=="http://localhost:5001"
    assert "AWS_ENDPOINT_URL_S3" not in os.environ and "AWS_PROFILE" not in os.environ
    assert "AWS_SESSION_TOKEN" not in os.environ
    assert os.environ["AWS_CONFIG_FILE"]==os.devnull and os.environ["AWS_SHARED_CREDENTIALS_FILE"]==os.devnull
    assert os.environ["DELIVERY_MODE"]=="DEMO_OUTBOX" and os.environ["SES_SENDER"]==""
    assert os.environ["BEDROCK_ENABLED"]=="false" and os.environ["LOCAL_DEMO"]=="true"


def test_browser_preconnect_cannot_block_health_requests():
    import socket
    import threading
    from urllib.request import urlopen
    from wsgiref.simple_server import make_server

    path=Path(__file__).resolve().parents[1]/"local_demo.py"
    spec=importlib.util.spec_from_file_location("demo_preconnect",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    accepted=threading.Event()

    class ObservedRequests(module.QuietRequests):
        def setup(self):
            super().setup()
            accepted.set()

    def health(environ,start_response):
        start_response("200 OK",[("Content-Type","text/plain"),("Content-Length","2")])
        return [b"ok"]

    with make_server("127.0.0.1",0,health,server_class=module.LocalHTTPServer,
                     handler_class=ObservedRequests) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        idle=socket.create_connection(server.server_address,timeout=2)
        try:
            assert accepted.wait(2),"Idle browser connection was not accepted"
            with urlopen(f"http://127.0.0.1:{server.server_port}/health",timeout=3) as response:
                assert response.status==200 and response.read()==b"ok"
        finally:
            idle.close()
            server.shutdown()
            thread.join(timeout=3)
