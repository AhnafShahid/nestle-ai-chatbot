#!/bin/bash

# Fill these values from Azure Portal
AZURE_WEBAPP_NAME="your-app-name"
AZURE_RESOURCE_GROUP="your-resource-group"

# Login to Azure
az login

# Create Resource Group
az group create --name $AZURE_RESOURCE_GROUP --location eastus

# Create App Service Plan
az appservice plan create \
  --name nestle-chatbot-plan \
  --resource-group $AZURE_RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --name $AZURE_WEBAPP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --plan nestle-chatbot-plan \
  --runtime "PYTHON:3.9"

# Set environment variables
az webapp config appsettings set \
  --name $AZURE_WEBAPP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --settings \
    HF_API_KEY=$HF_API_KEY \
    NEO4J_URI=$NEO4J_URI \
    NEO4J_USER=$NEO4J_USER \
    NEO4J_PASSWORD=$NEO4J_PASSWORD

# Deploy from local Git
az webapp deployment source config-local-git \
  --name $AZURE_WEBAPP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP

echo "Deployment complete! Your app will be available at:"
echo "https://$AZURE_WEBAPP_NAME.azurewebsites.net"