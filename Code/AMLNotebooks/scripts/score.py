# +
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

import argparse
import os
from azureml.core import Dataset, Datastore, Run, Workspace
from azureml.data import OutputFileDatasetConfig
from azureml.core.model import Model
import pandas as pd
import numpy as np
import sys
import joblib

import pipeline_library as pl

def score_pipeline(customerData,resident1Data,resident2Data,leaseData,paymentData,surveyData,workorderData, config):
    print("scoring ...")
    pl.pipeline_steps(customerData,resident1Data,resident2Data,leaseData,paymentData,surveyData,workorderData, config)
    return 

parser = argparse.ArgumentParser("score")

parser.add_argument("--input_data1", type=str, help="data 1")
parser.add_argument('--output_path', dest='output_path', required=True)
parser.add_argument('--output_datastore', dest='output_datastore', required=True)

args = parser.parse_args()

run = Run.get_context()
ws = run.experiment.workspace

print("geting datasets ...")

customerData = Run.get_context().input_datasets['customer_dataset']

resident1Data = Dataset.get_by_name(ws, name='Residents1Data')
resident2Data = Dataset.get_by_name(ws, name='Residents2Data')
leaseData = Dataset.get_by_name(ws, name='LeasesData')
paymentData = Dataset.get_by_name(ws, name='PaymentsData')
surveyData = Dataset.get_by_name(ws, name='SurveysData')
workorderData = Dataset.get_by_name(ws, name='WorkOrdersData')


print("Output Location", args.output_datastore + args.output_path)

# Load Model 
print("loading model ...")
#model_path = Model.get_model_path("lease_renewal_model", _workspace = ws,version = 1)
model_path = Model.get_model_path("model", _workspace = ws)
print("model_path : ", model_path)
model = joblib.load(model_path)


config = {
    "output_datastore" : args.output_datastore,
    "output_path" : args.output_path,
    "model" : model,
    "run" : run,
    "workspace": ws,
    "step_type" : "test"
}

score_pipeline(customerData,resident1Data,resident2Data, leaseData, paymentData,surveyData,workorderData, config)
