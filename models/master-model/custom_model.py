import os
import yaml
import pandas as pd
from helper import *
from requests_futures.sessions import FuturesSession
from io import StringIO
from datarobot_drum import RuntimeParameters
import numpy as np
import logging 
import time

logging.basicConfig(level=logging.INFO)
logging.basicConfig(
                format="{} - %(levelname)s - %(asctime)s - %(message)s".format("debug-loggers"),
        )
logger = logging.getLogger(__name__)
logger.setLevel("WARNING")


class RoutingModel(object):
    def __init__(self, code_dir: str):

        with open(os.path.join(code_dir, "routing_config.yaml"), "r") as f:
            self.routing_config = yaml.load(f, Loader=yaml.FullLoader)
        try:
            self.api_token = RuntimeParameters.get("DATAROBOT_API_TOKEN")["apiToken"]
        except:
            self.api_token = os.environ["DATAROBOT_API_TOKEN"]

        self.concurrency = 4
        self.session = FuturesSession(max_workers=self.concurrency)

    def retry_any_bad_future(self, future):
        result = future.result() 
        status_code = result.status_code 
        if status_code < 300:
            return future 
        elif status_code == 503:
            # 503 is associated with DataRobot spinning up more inference resources.
            logger.warning(result.content.decode("UTF-8"))
            logger.warning("retrying request. hang tight")
            orig_request = result.request
            url = orig_request.url 
            headers = orig_request.headers 
            data = orig_request.body 
            new_future = self.session.post(**dict(url = url, headers = headers), data=data)
            return new_future
        else:
            return future
        
    def wait_for_futures(self, futures):
        logger.info("waiting for predictions requests to complete")
        c = 0
        while not all( [r.done() for r in futures]):
            time.sleep(5)
            if np.mod(c, 500000) == 0:
                logger.info(f"number requests {sum([1 if r.done() else 0 for r in futures])}")
                # logger.info(f"still running. currently {(time.time_ns() - fstart) / 1e9} seconds and counting")
            c += 1
        successful = [future.result().status_code < 300 for future in futures]
        if all(successful):
            return futures
        else:
            futures = [ self.retry_any_bad_future(future) for future in futures ]
            return self.wait_for_futures(futures)

    def entry_to_payload(self, entry):
        url_payload = make_datarobot_deployment_url_payload(
            deployment_id=entry["deployment_id"],
            api_url=entry["url"],
            api_key=self.api_token ,
            datarobot_key=None,
            passthrough_columns=entry["passthrough_columns"],
        )
        return url_payload

    def predict(self, df):
        predictions = []
        for entry in self.routing_config:
            url_payload = self.entry_to_payload(entry)
            resp = requests.post(**url_payload, data=df.to_csv(index=False)).content
            predictions.append({"tag": entry["tag"], "predictions": resp.decode()})
        return predictions

    def futures_predict(self, df):
        responses = []
        results = []
        for entry in self.routing_config:
            url_payload = self.entry_to_payload(entry)
            responses.append(
                    self.session.post(**url_payload, data=df.to_csv(index=False)),
            )
        response = self.wait_for_futures(responses)
        responses = [ (entry["tag"], resp) for entry, resp in zip(self.routing_config, responses)]
        for tag, future in responses:
            # resp = future.result().json()
            resp = future.result().content
            # results.append({"tag": tag, "predictions": resp["data"]})
            results.append({"tag": tag, "predictions": resp.decode()})
        return results
