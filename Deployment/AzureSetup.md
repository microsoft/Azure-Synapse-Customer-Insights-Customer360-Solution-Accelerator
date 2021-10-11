# Setup Guide 
Please follow the steps below to set up the Azure environment

# Step 1: Download Files
Clone or download this repository and navigate to the project's root directory.

# Step 2: Synapse Security Access

### Step 2.1: Add your IP address to Synapse firewall
Before you can upload assests to the Synapse Workspace you will need to add your IP address:
1. Go to the Synapse resouce you created in the previous step. 
2. Navigate to `Networking` under `Security` on the left hand side of the page.
3. At the top of the screen click `+ Add client IP`
    ![Update Firewalls](./img/deploy-firewall.png)  
4. Your IP address should now be visable in the IP list

### Step 2.2: Update storage account permisions 
In order to perform the necessary actions in Synapse workspace, you will need to grant more access.
1. Go to the Azure Data Lake Storage Account created above
2. Go to the `Access Control (IAM) > + Add > Add role assignment` 
3. Now click the Role dropdown and select `Storage Blob Data Contributor`
    - Search for your username and add
4. Click `Save` at the bottom

[Learn more](https://docs.microsoft.com/azure/synapse-analytics/security/how-to-set-up-access-control)

# Step 3: Upload Customer 360 Sample Dataset
1. Launch the Synapse workspace [Synapse Workspace](https://ms.web.azuresynapse.net/)
2. Select the `subscription` and `workspace` name you are using for this solution accelerator
3. In Synapse Studio, navigate to the `Data` Hub
4. Select `Linked`
5. Under the category `Azure Data Lake Storage Gen2` you'll see an item with a name like `xxxxx(xxxxx- Primary)`
6. Select the container named `Data (Primary)`, select "New Folder" enter `sourcedata` and select "Create" 
7. Select the `sourcedata` folder, select `Upload` and select following sample data files downloaded from [Data](./Data/) folder
	- `residents.csv`
	- `leases.csv`
	- `payments.csv`
	- `surveys.csv`
	- `workorders.csv`


# Step 4: Upload Assets and Run Noteboks
1. Launch the Synapse workspace [Synapse Workspace](https://ms.web.azuresynapse.net/)
2. Go to `Develop`, click the `+`, and click `Import` to select all notebooks from this repository's [folder](./Code/SynapseNotebooks)
3. For each of the notebooks, select `Attach to > spark1` in the top dropdown
4. Configure the parameters in all 6 notebooks 
	* Note: Only change the parameters but do not run all the notebooks. You will run notebooks 1-5 after the Customer Insights set up. 
5. Run the following notebook
	* `00_prepare_sourcedata_for_ci.ipynb`
	
	
# Step 5: Set up the Customer Insights 
## Step 5.1: Add Dynamics 365 AI for Customer Insights Synapse Security Access 
In order to perform the necessary actions in Customer Insights, you will need to grant more access.
[Follow the steps here](https://docs.microsoft.com/en-us/dynamics365/customer-insights/audience-insights/connect-service-principal#grant-permissions-to-the-service-principal-to-access-the-storage-account) to grant the Dynamics 365 AI Customer Insights access to the ADLS Gen 2 storage account you are using for this solution.
## Step 5.2: Set Up CI
1. Navigate to the [CI Set Up Documentaion](./CustomerInsightsSetup.md)

# Step 6: Set up Synapse Pipeline
In order to run the pipelines, you will need to grant more access.
1. Go to the Azure Machine Learning Service created above
2. Go to the `Access Control (IAM) > + Add > Add role assignment` 
3. Now click the Role dropdown and select `Contributor`
    - Search for your Synapse Workspace and add
4. Click `Save` at the bottom

## Step 6.1: Training Pipeline 
In this step you will create the Training Pipeline 
* **Note:** You will need to manually connect each object in the pipeline.

1. Launch the Synapse workspace [Synapse Workspace](https://ms.web.azuresynapse.net/)
2. Go to `Integration`, click `+` and click `Pipeline` 
3. Under Properties provide the pipeline with the following name `TrainingPipeline`
4. Click the "{}" button at the top right corner to open the Code window
5. Copy and paste the contents of [TrainingPipeline.json](./Code/SynapsePipelines/TrainingPipeline.json)
6. Click OK to apply
7. Click "Publish All" > "Publish"
8. Trigger the pipeline
	* In the designer, click "Add Trigger" > "Trigger Now". The final pipeline should look like:
	![TrainingPipeline](./img/TrainingPipeline.png)

## Step 6.2: Inferencing Pipeline
In this step you will create the Inferencing Pipeline 
* **Note:** You will need to manually connect each object in the pipeline.

1. Launch the Synapse workspace [Synapse Workspace](https://ms.web.azuresynapse.net/)
2. Go to `Integration`, click `+` and click `Pipeline` 
3. Under Properties provide the pipeline with the following name `InferencingPipeline`
4. Click the "{}" button at the top right corner to open the Code window
5. Copy and paste the contents of [InferencingPipeline.json](./Code/SynapsePipelines/InferencingPipeline.json)
6. Click OK to apply
7. Click "Publish All" > "Publish"
8. Trigger the pipeline
	* In the designer, click "Add Trigger" > "Trigger Now". The final pipeline should look like:
	![InferencingPipeline](./img/InferencingPipeline.png)

# Step 7: Run Notebook  
1. Launch the Synapse workspace [Synapse Workspace](https://ms.web.azuresynapse.net/)
4. Configure the parameters and Run the notebooks in the following order
	* `5_prepare_predictionsdata_for_ci.ipynb`


# Step 8: CI Lease Renewal Predictions 
1. Navigate to step 12 in the [CI Set Up Documentaion](./CustomerInsightsSetup.md)