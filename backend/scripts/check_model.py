from app.training.model_predictor import load_quality_model, predict_quality_label

m = load_quality_model()
print("model_loaded:", bool(m))
print("feature_names_in_:", getattr(m, "feature_names_in_", None))
try:
    print("sample prediction:", predict_quality_label({}))
except Exception as e:
    print("prediction_error:", repr(e))
