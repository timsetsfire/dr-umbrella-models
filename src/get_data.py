import pandas as pd 
import uuid
import datarobot as dr 
import yaml
def get_data(scoring_data_yaml):
    with open(scoring_data_yaml, "r") as f:
        dataset_config = yaml.load(f, Loader =  yaml.SafeLoader)
    scoring_dataset_id = dataset_config.get("scoring_dataset")["id"]
    df = dr.Dataset.get(scoring_dataset_id).get_as_dataframe()
    df.columns = [c.lower() for c in df.columns]
    df["ASSOCIATION_ID"] = [str(uuid.uuid1()) for i in range(df.shape[0])]
    return df
