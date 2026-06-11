# Text2STL Fine-Tuning Workflows

This project supports two training-data paths.

## Version 1: UI Feedback

The Streamlit app can save a user rating after every generation. Each feedback row is written to:

```text
outputs/feedback/feedback.jsonl
```

Each record includes:

```text
prompt
generated CadQuery code
rating
free-text feedback
validation report
whether the user accepted it for training
```

This does not train the model immediately. It creates examples for later supervised fine-tuning.

Prepare accepted feedback examples:

```powershell
python training/prepare_sft_dataset.py `
  --feedback outputs/feedback/feedback.jsonl `
  --out training/out/feedback_sft.jsonl `
  --min-rating 4
```

Only records that are accepted for training, have rating >= 4, have generated code, and passed STL validation are included.

## Version 2: Curated Dataset

You can also provide a prepared JSONL dataset. Each row should have at least:

```json
{"prompt": "Make a simple chair", "code": "def build_model():\n    import cadquery as cq\n    ...\n    return model", "validation_pass": true, "rating": 5}
```

Prepare a curated dataset:

```powershell
python training/prepare_sft_dataset.py `
  --dataset training/example_dataset.jsonl `
  --out training/out/curated_sft.jsonl `
  --min-rating 4
```

## Version 3: Text-to-CadQuery Dataset

For model training, we use the public Text-to-CadQuery dataset:

```text
https://huggingface.co/ricemonster/NeurIPS11092/tree/main/data
```

It contains prompt-completion JSONL files for natural-language-to-CadQuery training. The converter wraps the raw CadQuery into this app's `build_model()` format, removes dataset STL export calls, and scales source meter dimensions to millimeters by default. Keep the raw files outside this repo so they are not committed to GitHub:

```powershell
$env:TEXT2STL_DATASET_DIR = "D:\FMI\LLM_proekt\datasets\text-to-cadquery"
```

Download and normalize the dataset into this project's curated format:

```powershell
python training/prepare_text_to_cadquery_dataset.py `
  --data-dir $env:TEXT2STL_DATASET_DIR `
  --out training/out/text_to_cadquery_curated.jsonl
```

For a quick test, use a small sample:

```powershell
python training/prepare_text_to_cadquery_dataset.py `
  --data-dir $env:TEXT2STL_DATASET_DIR `
  --split test `
  --limit-per-file 100 `
  --out training/out/text_to_cadquery_sample.jsonl
```

Convert the normalized dataset to chat-style SFT records for Qwen:

```powershell
python training/prepare_sft_dataset.py `
  --dataset training/out/text_to_cadquery_curated.jsonl `
  --out training/out/text_to_cadquery_sft.jsonl `
  --min-rating 0
```

You can combine both paths:

```powershell
python training/prepare_sft_dataset.py `
  --feedback outputs/feedback/feedback.jsonl `
  --dataset training/example_dataset.jsonl `
  --out training/out/combined_sft.jsonl `
  --min-rating 4
```

## Fine-Tuning

The output files are supervised fine-tuning records in chat-message JSONL format. They are ready to feed into a LoRA/QLoRA training job for a coder model.

Run training on a machine with an NVIDIA GPU. First install the training stack:

```powershell
pip install -r training/requirements-train.txt
```

Start with a small smoke test:

```powershell
python training/train_qwen_lora.py `
  --dataset training/out/text_to_cadquery_sft.jsonl `
  --model-name Qwen/Qwen3-8B `
  --output-dir training/out/qwen3-8b-text2stl-lora-smoke `
  --max-samples 2000
```

If that works, run the full LoRA/QLoRA training:

```powershell
python training/train_qwen_lora.py `
  --dataset training/out/text_to_cadquery_sft.jsonl `
  --model-name Qwen/Qwen3-8B `
  --output-dir training/out/qwen3-8b-text2stl-lora
```

The output is a LoRA adapter, not a full standalone model. Keep the validation and repair loop even after fine-tuning, because CAD generation can still produce invalid geometry.
