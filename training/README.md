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

The recommended next step is to collect at least a few hundred validated examples before training. Keep the validation and repair loop even after fine-tuning, because CAD generation can still produce invalid geometry.
