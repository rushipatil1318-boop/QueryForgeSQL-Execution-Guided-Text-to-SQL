import io
import json
import unittest
from unittest.mock import patch
import urllib.error

from queryforgesql.config import ModelSettings
from queryforgesql.providers import HTTPProvider, ModelError


class ProviderTests(unittest.TestCase):
    def test_ollama_sends_bounded_seeded_nonstreaming_request(self):
        response = {"model": "test", "message": {"content": "SELECT 1"}, "done": True,
                    "prompt_eval_count": 10, "eval_count": 3}
        provider = HTTPProvider(ModelSettings(provider="ollama", model="test"))
        with patch("urllib.request.OpenerDirector.open", return_value=io.BytesIO(json.dumps(response).encode())) as request:
            completion = provider.complete([{"role": "user", "content": "q"}], question_id="1", seed=42)
        body = json.loads(request.call_args.args[0].data)
        self.assertFalse(body["stream"])
        self.assertEqual(body["options"]["seed"], 42)
        self.assertEqual(completion.prompt_tokens, 10)
        self.assertEqual(completion.text, "SELECT 1")

    def test_chat_completion_reads_usage_and_key_from_environment(self):
        settings = ModelSettings(provider="chat_completions", model="test", endpoint="https://example.com/v1/chat/completions")
        response = {"model": "test", "choices": [{"message": {"content": "SELECT 1"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 9, "completion_tokens": 2}, "system_fingerprint": "v1"}
        with patch.dict("os.environ", {"QUERYFORGE_API_KEY": "test-secret"}), patch("urllib.request.OpenerDirector.open", return_value=io.BytesIO(json.dumps(response).encode())) as request:
            completion = HTTPProvider(settings).complete([], question_id="1", seed=42)
        self.assertEqual(request.call_args.args[0].get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(completion.fingerprint, "v1")
        self.assertEqual(completion.completion_tokens, 2)

    def test_http_error_is_one_call_and_does_not_expose_body(self):
        error = urllib.error.HTTPError("https://example.com", 401, "private", {}, io.BytesIO(b"secret"))
        provider = HTTPProvider(ModelSettings(provider="ollama"))
        with patch("urllib.request.OpenerDirector.open", side_effect=error) as request:
            with self.assertRaises(ModelError) as caught:
                provider.complete([], question_id="1", seed=42)
        self.assertEqual(request.call_count, 1)
        self.assertNotIn("secret", str(caught.exception))

    def test_incomplete_output_is_not_executed(self):
        response = {"message": {"content": "SELECT"}, "done": True, "done_reason": "length"}
        with patch("urllib.request.OpenerDirector.open", return_value=io.BytesIO(json.dumps(response).encode())):
            with self.assertRaises(ModelError):
                HTTPProvider(ModelSettings(provider="ollama")).complete([], question_id="1", seed=42)

    def test_missing_text_is_recorded_as_model_error(self):
        response = {"message": {"content": None}, "done": True}
        with patch("urllib.request.OpenerDirector.open", return_value=io.BytesIO(json.dumps(response).encode())):
            with self.assertRaises(ModelError):
                HTTPProvider(ModelSettings(provider="ollama")).complete([], question_id="1", seed=42)


if __name__ == "__main__":
    unittest.main()
