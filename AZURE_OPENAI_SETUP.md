# Azure OpenAI Setup for Classification

## Overview

The classification module now uses **Azure OpenAI** instead of Google Gemini.

- **Classification (Step 5)**: Azure OpenAI
- **Evaluation (Step 6)**: Google Gemini (unchanged)

## Configuration

### 1. Update .env File

Add your Azure OpenAI credentials to `.env`:

```env
# Azure OpenAI API (for Classification)
AZURE_OPENAI_API_KEY=your_azure_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### 2. Get Azure OpenAI Credentials

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Azure OpenAI resource
3. Get the following:
   - **API Key**: Keys and Endpoint → Key 1
   - **Endpoint**: Keys and Endpoint → Endpoint
   - **Deployment**: Deployments → Your deployment name (e.g., "gpt-4")

### 3. Install Dependencies

```bash
pip install openai>=1.0.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## What Changed

### Modified Files

1. **classification/tcs_classifier.py**
   - Changed from `google.generativeai` to `openai.AzureOpenAI`
   - Updated `__init__` to accept Azure parameters
   - Updated `_get_client()` to use Azure OpenAI client
   - Updated `_call_llm()` to use chat completions API

2. **config/config.py**
   - Added Azure OpenAI configuration variables
   - Loads from environment variables

3. **.env / .env.example**
   - Added Azure OpenAI credentials

4. **requirements.txt**
   - Added `openai>=1.0.0`

5. **run_pipeline.py**
   - Updated to pass Azure credentials to TCSClassifier

### Code Changes

**Before (Gemini):**
```python
classifier = TCSClassifier(api_key=GEMINI_API_KEY)
```

**After (Azure OpenAI):**
```python
classifier = TCSClassifier(
    api_key=AZURE_OPENAI_API_KEY,
    endpoint=AZURE_OPENAI_ENDPOINT,
    deployment=AZURE_OPENAI_DEPLOYMENT,
    api_version=AZURE_OPENAI_API_VERSION
)
```

## API Comparison

### Gemini (Old)
```python
import google.generativeai as genai

genai.configure(api_key=api_key)
client = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config={
        "temperature": 0.3,
        "response_mime_type": "application/json"
    }
)
response = client.generate_content(prompt)
```

### Azure OpenAI (New)
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)
response = client.chat.completions.create(
    model=deployment,
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ],
    temperature=0.3,
    response_format={"type": "json_object"}
)
```

## Benefits of Azure OpenAI

✅ **Enterprise Ready** - Better for corporate environments
✅ **Data Privacy** - Data stays in your Azure tenant
✅ **Compliance** - Meets enterprise compliance requirements
✅ **SLA** - Enterprise-grade SLA and support
✅ **Integration** - Better integration with Azure services
✅ **Cost Control** - Better cost management and quotas

## Testing

Test the configuration:

```bash
python -c "from config.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT; print(f'API Key: {AZURE_OPENAI_API_KEY[:20]}...'); print(f'Endpoint: {AZURE_OPENAI_ENDPOINT}')"
```

Run the pipeline:

```bash
python run_pipeline.py
```

You should see:
```
🎨 Step 5: Classifying themes, industries, and technologies...
   Using: Azure OpenAI
```

## Troubleshooting

### Error: "Resource not found"
- Check your `AZURE_OPENAI_ENDPOINT` is correct
- Ensure it ends with `/`

### Error: "Invalid API key"
- Verify `AZURE_OPENAI_API_KEY` in .env
- Check the key is active in Azure Portal

### Error: "Deployment not found"
- Verify `AZURE_OPENAI_DEPLOYMENT` matches your deployment name
- Check deployment exists in Azure Portal → Deployments

### Error: "API version not supported"
- Update `AZURE_OPENAI_API_VERSION` to a supported version
- Current: `2024-02-15-preview`

## Recommended Models

For classification, we recommend:

1. **gpt-4** - Best quality, higher cost
2. **gpt-4-turbo** - Good balance of quality and speed
3. **gpt-35-turbo** - Faster, lower cost (may reduce quality)

Update in .env:
```env
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo
```

## Cost Estimation

Classification typically uses:
- ~2,000-3,000 tokens per idea
- For 100 ideas: ~200,000-300,000 tokens

**Approximate costs (as of 2024):**
- GPT-4: $0.03/1K input tokens = ~$6-9 per 100 ideas
- GPT-4-Turbo: $0.01/1K input tokens = ~$2-3 per 100 ideas
- GPT-3.5-Turbo: $0.0005/1K input tokens = ~$0.10-0.15 per 100 ideas

## Rollback to Gemini

If you need to rollback to Gemini:

1. Restore the old `tcs_classifier.py` from git history
2. Update `run_pipeline.py` to use Gemini API key
3. Remove Azure OpenAI dependencies

Or keep both and switch via environment variable (future enhancement).
