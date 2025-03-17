import pandas as pd 
import uuid
import datarobot as dr 
import yaml

def write_predictions(preds, scoring_data_yaml):
    with open(scoring_data_yaml, "r") as f:
        dataset_config = yaml.load(f, Loader =  yaml.SafeLoader)
    prediction_dataset = dataset_config.get("prediction_dataset", {})
    if prediction_dataset_id := prediction_dataset.get("id"):
        dataset = dr.Dataset.create_version_from_in_memory_data(prediction_dataset_id, preds)
    else:
        dataset = dr.Dataset.create_from_in_memory_data(preds, fname = "INSURANCE_PREDICTIONS")
    dataset_config["prediction_dataset"] = dataset.__dict__
    with open(scoring_data_yaml, "w") as f:
        f.write( yaml.dump(dataset_config) )
    return True
