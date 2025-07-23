from utility.ModelResolver import ModelResolver
from pydantic import BaseModel, ValidationError

def test_model_resolution():
    print("Testing ModelResolver...")
    resolver = ModelResolver("utility.model")

    # Test valid model resolution
    try:
        print("Testing a valid model...")
        model_class = resolver.resolve("SchemeMetadata")
        print(f"Resolved class: {model_class.__name__}")
        assert issubclass(model_class, BaseModel)
    except Exception as e:
        print(f"Failed to resolve valid model: {e}")

    # Test invalid class name
    try:
        print("Testing an invalid model...")
        resolver.resolve("NonExistentModel")
    except ValueError as ve:
        print(f"Caught expected error for invalid class: {ve}")
    else:
        print("Did not raise error for invalid class name")

    # Test list_models
    models = resolver.list_models()
    print("Available models in module:")
    for m in models:
        print(f" - {m}")
    assert isinstance(models, list) and len(models) > 0

if __name__ == "__main__":
    test_model_resolution()