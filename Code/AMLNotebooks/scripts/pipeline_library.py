# +
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

import argparse
import os
import tempfile
from azureml.core import Dataset, Run, Datastore
import pandas as pd
import numpy as np
import sys
import joblib
from azureml.core.model import Model
from azureml.core import Workspace
from sklearn.linear_model import LogisticRegression
import datetime

def pipeline_steps(customerData,resident1Data,resident2Data,leaseData,paymentData,surveyData,workorderData,config):
    #variables from config file
    output_datastore = config["output_datastore"]
    output_path = config["output_path"]
    model = config["model"]
    run = config["run"] 
    step_type = config["step_type"]
    workspace = config["workspace"]
    
    #prepare data
    df_customer = customerData.to_pandas_dataframe().fillna(value=np.nan)
    
    df_cust_s1 = df_customer[['CustomerId','sourcedata_residents_source1_cid','SurveyEmail']]
    df_cust_s1.columns = ['CustomerId','cid','SurveyEmail']
    df_cust_s2 = df_customer[['CustomerId','sourcedata_residents_source2_cid','SurveyEmail']]
    df_cust_s2.columns = ['CustomerId','cid','SurveyEmail']
    df_customer_ids = pd.concat([df_cust_s1, df_cust_s2])
    df_customer_ids['cid'] = df_customer_ids['cid'].astype(np.float).astype("Int64")

    df_residentdata = pd.concat([resident1Data.to_pandas_dataframe().fillna(value=np.nan),
                                 resident2Data.to_pandas_dataframe().fillna(value=np.nan)])
    
    #Initial Lease Details
    df_lease_initial = leaseData.to_pandas_dataframe().fillna(value=np.nan)[["cid","pid","uid","EndDate","LeaseTerm","Type"]]
    df_lease_initial = df_lease_initial[df_lease_initial['Type'] == 'Application']
    df_lease_initial = df_lease_initial.drop_duplicates(keep="last")
    df_lease_initial = df_lease_initial[["cid","pid","uid","LeaseTerm"]]
    df_lease_initial.columns = ["cid","pid","uid","InitialLeaseTerm"]
    df_lease_initial = df_lease_initial.drop_duplicates(keep="last")
    df_lease_initial = df_lease_initial.reset_index(drop=True)
    #print(df_lease_initial)

    #Renewals
    df_lease_renewal = leaseData.to_pandas_dataframe().fillna(value=np.nan)[["cid","pid","uid","lid","EndDate","LeaseTerm","Type"]]
    df_lease_renewal = df_lease_renewal[df_lease_renewal['Type'] == 'Renewal']
    df_lease_renewal['num_renewals'] = df_lease_renewal.groupby(['cid','pid','uid'])['lid'].transform(len)
    #df_lease_renewal['isRenewed'] = np.where(df_lease_renewal['num_renewals']>=1, 'Y', 'N')
    df_lease_renewal = df_lease_renewal.drop_duplicates(keep="last")
    df_lease_renewal = df_lease_renewal.reset_index(drop=True)
    #print(df_lease_renewal)


    df_lease_moveout = leaseData.to_pandas_dataframe().fillna(value=np.nan)[["cid","pid","uid","lid","StartDate","EndDate","MoveOutDate","LeaseTerm","Type"]]
    df_lease_moveout['min_LeaseBeginDate'] = df_lease_moveout.groupby(['cid','pid','uid','lid'])['StartDate'].transform(min)
    df_lease_moveout['max_LeaseEndDate'] = df_lease_moveout.groupby(['cid','pid','uid','lid'])['EndDate'].transform(max)
    df_lease_moveout['max_MoveOutDate'] = df_lease_moveout.groupby(['cid','pid','uid','lid'])['MoveOutDate'].transform(max)
    df_lease_moveout['isMovedOut'] = np.where(df_lease_moveout['max_MoveOutDate'].isna(), 'N', 'Y')
    df_lease_moveout['diffMoveOutDays'] = df_lease_moveout['max_MoveOutDate'] - df_lease_moveout['max_LeaseEndDate']
    df_lease_moveout['diffMoveOutDays'] = df_lease_moveout['diffMoveOutDays'].dt.days
    df_lease_moveout['isEarlyMoveOut'] = np.where(df_lease_moveout['diffMoveOutDays'] < 0, 'Y', 'N')
    df_lease_moveout = df_lease_moveout.sort_values(by="EndDate").drop_duplicates(subset=['cid','pid','uid'], keep="last")
    df_lease_moveout = df_lease_moveout.reset_index(drop=True)
    #print(df_lease_moveout)

    df_leasedata = df_lease_initial.merge(df_lease_renewal,on=["cid","pid","uid"],how='left')
    df_leasedata = df_leasedata.merge(df_lease_moveout,on=["cid","pid","uid"],how='left')

    df_leasedata['num_renewals'] = df_leasedata['num_renewals'].fillna(0)
    df_leasedata['isRenewed'] = np.where(df_leasedata['num_renewals']>=1, 1, 0)

    df_leasedata.drop(df_leasedata.filter(regex='_x$').columns.tolist(),axis=1, inplace=True)
    df_leasedata.drop(df_leasedata.filter(regex='_y$').columns.tolist(),axis=1, inplace=True)
    
    df_leasedata = df_leasedata[['cid','pid','uid','InitialLeaseTerm','num_renewals','isRenewed']]
    #print(df_leasedata)
    # get workorder details
    #import re

    df_workorders = workorderData.to_pandas_dataframe().fillna(value=np.nan)[["cid","pid","uid","workorder_type","ServiceRequestDate","ServiceCompleteDate"]]
    df_workorders = df_workorders[["cid","pid","uid","workorder_type"]]
    df_workorders['workorder_type'] = 'WO_' + df_workorders['workorder_type']
    df_workorders['workorder_type'] = df_workorders['workorder_type'].str.replace(r'[^0-9a-zA-Z_$]+', '')
    df_workorders['num_workorders'] = df_workorders.groupby(['cid','pid','uid','workorder_type'])['cid'].transform(len)
    df_workorders = df_workorders.drop_duplicates(keep="last")
    df_workorders = df_workorders.reset_index(drop=True)

    pivoted=df_workorders.pivot_table(index=['cid','pid','uid',], columns=['workorder_type'], values='num_workorders', aggfunc="max").fillna(0)
    df_workorders = pd.DataFrame(pivoted.to_records())
    df_workorders = df_workorders.reset_index(drop=True)
    df_workorders

    #get survey data

    df_surveydata = surveyData.to_pandas_dataframe()[["pid","surveytype","question","answer",'Email']]
    df_surveydata = df_surveydata.merge(df_customer_ids[['SurveyEmail','cid']],left_on=["Email"],right_on=["SurveyEmail"], how='inner')
    
    df_surveydata = df_surveydata[["cid","pid","surveytype","question","answer"]] 
    
    df_surveydata['Survey_Question'] = df_surveydata['surveytype'] + '_' + df_surveydata['question']
    df_surveydata['answer'] = df_surveydata['answer'].astype(int)
    df_surveydata = df_surveydata[["cid","pid","Survey_Question","answer"]]
    df_surveydata['Survey_Question'] = df_surveydata['Survey_Question'].str.replace(r'[^0-9a-zA-Z_$]+', '')
    df_surveydata['avg_SurveryAnswer'] = df_surveydata.groupby(['cid','pid','Survey_Question'])['answer'].transform('mean')
    df_surveydata = df_surveydata[['cid','pid','Survey_Question','avg_SurveryAnswer']]
    df_surveydata = df_surveydata.drop_duplicates(keep="last")
    df_surveydata = df_surveydata.reset_index(drop=True)
   
    pivoted=df_surveydata.pivot_table(index=['cid','pid'], columns=['Survey_Question'], values='avg_SurveryAnswer', aggfunc="max").fillna(0)
    df_surveydata = pd.DataFrame(pivoted.to_records())
    df_surveydata = df_surveydata.reset_index(drop=True)
    
    df_joined = df_leasedata.merge(df_workorders,on=["cid","pid","uid"], how='left')
    
    df_joined = df_joined.merge(df_surveydata,on=["cid","pid"], how='left')
    df_joined.drop(df_joined.filter(regex='_x$').columns.tolist(),axis=1, inplace=True)
    df_joined.drop(df_joined.filter(regex='_y$').columns.tolist(),axis=1, inplace=True)
    
    df_joined = df_joined[['cid','pid','uid','InitialLeaseTerm','isRenewed','Movein_OverallSatisfaction','Renewal_OverallSatisfaction','WO_AirConditioning','WO_Dishwasher','WO_Washer']]
    
    
    df_customer_ids = df_customer_ids[['CustomerId','cid']]
    df_customer_ids.dropna(inplace=True)
    df_customer_ids['cid'] = df_customer_ids['cid'].astype("int64")
    
    df_joined = df_joined.merge(df_customer_ids[['CustomerId','cid']],on=["cid"], how='inner')

    df_joined.fillna(0,inplace = True)
    
    if step_type =="test":
        df_result = df_joined
        cols = [col for col in df_joined.columns if col not in ["isRenewed","CustomerId","cid","pid","uid"]]
        df_result = write_results(df_customer_ids, df_result, cols, output_datastore, output_path, model,run)
    elif step_type == "train":
        permuted_indices = np.random.permutation(df_joined.index)
        train_len = int(0.8*len(permuted_indices))
        train = df_joined.iloc[permuted_indices[:train_len]]
        test = df_joined.iloc[permuted_indices[train_len:]]
        cols = [col for col in train.columns if col not in ["isRenewed","CustomerId","cid","pid","uid"]]
        
        print("train columns")
        model_folder = config["model_folder"]
        model_name = config["model_name"]
        train_steps(train, test, cols, model_folder, model_name)

        print("register model")
        model_path = "./" + config["model_folder"] 
        description = config["description"]
        register_model(model_path, model_name, description, workspace)
    else:
        raise Exception("Invalid step type, allowed values are train and test")
    return 
    
def train_steps(train, test, cols, model_folder, model_name):
    print("training ...")
    clf = LogisticRegression()
    clf.fit(train[cols].values, train["isRenewed"].values)

    print('predicting ...')
    y_hat = clf.predict(test[cols].astype(int).values)

    acc = np.average(y_hat == test["isRenewed"].values)
    print('Accuracy is', acc)

    print("save model")
    os.makedirs('models', exist_ok=True)    
    joblib.dump(value=clf, filename= model_folder +'/'+ model_name + ".pkl")
    return

def register_model(model_path, model_name, description, ws):
    model = Model.register(model_path = model_path,
                        model_name = model_name,
                        description = description,
                        workspace = ws)
    return    


def write_results(df_customer_ids, df, cols, output_datastore, output_path, model, run):

    ws = run.experiment.workspace
    datastore = Datastore.get(ws, output_datastore)
    output_folder = tempfile.TemporaryDirectory(dir = "/tmp")
    filename = os.path.join(output_folder.name, os.path.basename(output_path))
    print("Output filename: {}".format(filename))

    try:
        os.remove(filename)
    except OSError:
        pass
    
    df["ScoredLabels"] = model.predict(df[cols].astype(int).values)
    df["ScoredProbabilities"] = model.predict_proba(df[cols].astype(int).values)[:,1]
    
    df = df[['CustomerId','ScoredLabels', 'ScoredProbabilities']]
    df = df.groupby(['CustomerId']).agg({'ScoredLabels':'max', 'ScoredProbabilities':'max'}).reset_index()
    df.columns = ['CustomerId','RenewalPredictionFlag', 'RenewalPredictionScore']
   
    # set CustomerID to index to remove the column1 columns in the dataframe
    df = df.set_index("CustomerId")
    print(df)

    directory_name =  os.path.dirname(output_path)
    print("Extracting Directory {} from path {}".format(directory_name, output_path))
    
    df.to_csv(filename)
    
    # Datastore.upload() is supported currently, but is being deprecated by Dataset.File.upload_directory()
    # datastore.upload(src_dir=output_folder.name, target_path=directory_name, overwrite=False, show_progress=True)
    # upload_directory can fail sometimes.
    output_dataset = Dataset.File.upload_directory(src_dir=output_folder.name, target = (datastore, directory_name))
    return df
# -


