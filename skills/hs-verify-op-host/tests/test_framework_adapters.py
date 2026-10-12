import hashlib
import importlib.util
from pathlib import Path

import pytest


PATH = Path(__file__).resolve().parent.parent / "scripts/training/framework_adapters.py"
spec = importlib.util.spec_from_file_location("framework_adapters", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_supported_framework_converter_flags():
    assert module.converter_framework("onnx") == "ONNX"
    assert module.converter_framework("tflite") == "TFLITE"


def test_unsupported_framework_is_explicit():
    with pytest.raises(ValueError, match="UNSUPPORTED_FRAMEWORK"):
        module.framework_name("mindir")


def test_source_hash_is_checked_before_framework_parser(tmp_path):
    model = tmp_path / "model.tflite"
    model.write_bytes(b"not a flatbuffer")
    with pytest.raises(ValueError, match="source model hash mismatch"):
        module.validate_source_model(model, "0" * 64, {"targets": []}, "tflite")


def test_tflite_builtin_code_uses_legacy_sentinel_rule():
    class OperatorCode:
        def __init__(self, modern, deprecated):
            self.modern = modern
            self.deprecated = deprecated

        def BuiltinCode(self):
            return self.modern

        def DeprecatedBuiltinCode(self):
            return self.deprecated

    assert module._builtin_code(OperatorCode(130, 127)) == 130
    assert module._builtin_code(OperatorCode(95, 95)) == 95
    assert module._builtin_code(OperatorCode(0, 42)) == 42
    assert module._builtin_code(OperatorCode(50, 127)) == 127


def test_tflite_missing_schema_is_not_silent():
    model = Path(__file__).resolve()
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="TFLite"):
        module.validate_source_model(model, digest, {"targets": []}, "tflite")
