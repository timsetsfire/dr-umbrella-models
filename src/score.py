from dotenv import load_dotenv
import pandas as pd
import os 
import logging
import logging
import sys
import requests
from requests_futures.sessions import FuturesSession
from io import BytesIO, StringIO
import numpy as np
import pandas as pd
import datarobot as dr
import uuid
import time 
import os

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)
load_dotenv(override = True) 


API_KEY = os.environ["DATAROBOT_API_TOKEN"]

def score(df: pd.DataFrame, DEPLOYMENT_ID): 
    # DEPLOYMENT_ID = "67c5f1b816996513f5a286ee"
    DEPLOYMENT_URL = f'https://app.datarobot.com/api/v2/deployments/{DEPLOYMENT_ID}/predictionsUnstructured' 
    def retry_any_bad_future(future):
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
            new_future = session.post(**dict(url = url, headers = headers), data=data)
            return new_future
        else:
            return future
    
    def wait_for_futures(futures, fstart):
        c = 0
        while not all( [r.done() for r in futures]):
            if np.mod(c, 5000000) == 0:
                logger.info(f"number of completed batches {sum([1 if r.done() else 0 for r in futures])}")
                logger.info(f"still running. currently {(time.time_ns() - fstart) / 1e9} seconds and counting")
                c += 1
                time.sleep(3)          
        successful = [future.result().status_code < 300 for future in futures]
        if all(successful):
            return futures
        else:
            futures = [ retry_any_bad_future(future) for future in futures ]
            return wait_for_futures(futures, fstart)
    
    MAX_MB_PER_REQUEST = 10
    used_bytes = sys.getsizeof(df.to_csv(index = False)) 
        # logger.info(f"memory usage is {used_bytes} bytes")    
    used_megabytes = (used_bytes / 1e6)
    realtime_batches = int(np.ceil(used_megabytes/MAX_MB_PER_REQUEST))
    realtime_concurrency = 4
    # logger.info(f"dataset size is {used_megabytes:1.3} MB")
    headers = {
        'Content-Type': 'application/text; charset=UTF-8',
            # 'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
    }
    params = {
        # "passthroughColumns": ['col1']
    }
    URL = DEPLOYMENT_URL
    bad_requests = []
    if realtime_batches == 1:
        fstart = time.time_ns()
        result = requests.post(
            URL, 
            headers = headers, 
            data = df.to_csv(index = False),
            params = params
        )
        if result.status_code < 300:
            logger.info(f"prediction request status code: {result.status_code}")
        else: 
            logger.error(f"prediction request status code: {result.status_code}")
            logger.error(result.content.decode("UTF-8"))
            raise Exception(result.content.decode("UTF-8"))
        try:
            out = result.json()
        except Exception as e:
            logger.error(e)
        fend = time.time_ns() 
    else:
        logger.info(f"making concurrent calls for scoring")
        logger.info(f"batches: {realtime_batches}, max workers: {realtime_concurrency}")
        responses = []
        out = []
        df_batches = np.array_split(df, realtime_batches)
        session = FuturesSession(max_workers=realtime_concurrency)
        url_payload = dict(url = URL, headers = headers, params = params)
        for b, df_batch in enumerate(df_batches):
            logger.info(f"scoring {df_batch.shape[0]} records in batch {b}")
            responses.append(session.post(**url_payload, data=df_batch.to_csv(index=False)))
        fstart = time.time_ns()
        responses = wait_for_futures(responses, fstart)
        logger.info(f"number of completed batches {sum([1 if r.done() else 0 for r in responses])}")
        
        for i, future in enumerate(responses):
            result = future.result() 
            status_code =result.status_code
            if status_code < 300:
                logger.info(f"batch {i} status code: {status_code}")
            else:
                logger.warning(f"batch {i} status code: {status_code}")
                logger.warning(result.content.decode("UTF-8"))
                bad_requests.append(future.result())
            response_payload = result.json()
            # Get results in CSV format
            # so = StringIO(raw_bytes.decode())
            # Display results
            out.append(response_payload)
        fend = time.time_ns() 
        # try:
        #     df_pred = pd.concat(df_pred)
        # except Exception as e:
        #     logger.error(e)
    logger.info("="*30)
    logger.info(f"number of seconds to complete scoring: {(fend - fstart)/1e9}")
    logger.info("="*30)
    return out
